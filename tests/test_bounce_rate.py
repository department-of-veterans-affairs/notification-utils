import datetime
import random
import uuid
import pytest
from unittest.mock import Mock
from freezegun import freeze_time

from notifications_utils.clients.redis.bounce_rate import (
    _current_time,
    RedisBounceRate,
    _hard_bounce_key,
    _notifications_key,
    _total_notifications_seeded_key,
    _total_hard_bounces_seeded_key,
)
from notifications_utils.clients.redis.redis_client import RedisClient


@pytest.fixture(scope="function")
def mocked_redis_pipeline():
    return Mock()


@pytest.fixture(scope="function")
def mocked_redis_client(app, mocked_redis_pipeline, mocker):
    app.config["REDIS_ENABLED"] = True
    return build_redis_client(app, mocked_redis_pipeline, mocker)


def build_redis_client(app, mocked_redis_pipeline, mocker):
    redis_client = RedisClient()
    redis_client.init_app(app)
    return redis_client


@pytest.fixture(scope="function")
def mocked_bounce_rate_client(mocked_redis_client, mocker):
    return build_bounce_rate_client(mocker, mocked_redis_client)


@pytest.fixture(scope="function")
def mocked_seeded_data_hours():
    hour_delta = datetime.timedelta(hours=1)
    hours = [datetime.datetime.now() - hour_delta]
    for i in range(23):
        hours.append(hours[i] - hour_delta)
    return hours


def build_bounce_rate_client(mocker, mocked_redis_client):
    bounce_rate_client = RedisBounceRate(mocked_redis_client)
    mocker.patch.object(bounce_rate_client._redis_client, "add_key_to_sorted_set")
    mocker.patch.object(
        bounce_rate_client._redis_client, "get_length_of_sorted_set", side_effect=[8, 20, 0, 0, 0, 8, 0, 0, 10, 20]
    )
    mocker.patch.object(
        bounce_rate_client._redis_client, "get_sorted_set_members_by_score", side_effect=[0, 0, 1, 2, 0, 0, 0, 0, 4, 8]
    )
    mocker.patch.object(bounce_rate_client._redis_client, "expire")
    return bounce_rate_client


@pytest.fixture(scope="function")
def mocked_service_id():
    return str(uuid.uuid4())


class TestRedisBounceRate:
    @freeze_time("2001-01-01 12:00:00.000000")
    def test_set_hard_bounce(self, mocked_bounce_rate_client, mocked_service_id):
        mocked_bounce_rate_client.set_sliding_hard_bounce(mocked_service_id)
        mocked_bounce_rate_client._redis_client.add_key_to_sorted_set.assert_called_with(
            _hard_bounce_key(mocked_service_id), _current_time(), _current_time()
        )

    @freeze_time("2001-01-01 12:00:00.000000")
    def test_set_total_notifications(self, mocked_bounce_rate_client, mocked_service_id):
        mocked_bounce_rate_client.set_sliding_notifications(mocked_service_id)
        mocked_bounce_rate_client._redis_client.add_key_to_sorted_set.assert_called_with(
            _notifications_key(mocked_service_id), _current_time(), _current_time()
        )

    @freeze_time("2001-01-01 12:00:00.000000")
    def test_get_bounce_rate(self, mocked_bounce_rate_client, mocked_service_id):
        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0.4

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0.5

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0

        answer = mocked_bounce_rate_client.get_bounce_rate(mocked_service_id)
        assert answer == 0.5

    def test_set_total_hard_bounce_seeded_with_24_hour_period(
        self, mocked_bounce_rate_client, mocked_service_id, mocked_seeded_data_hours
    ):
        for hour in mocked_seeded_data_hours:
            bounce_count = random.randint(1, 10)
            bounce_epoch = hour.replace(minute=0, second=0, microsecond=0).timestamp()
            mocked_bounce_rate_client.set_total_hard_bounce_seeded(mocked_service_id, hour, bounce_count)
            mocked_bounce_rate_client._redis_client.add_key_to_sorted_set.assert_called_with(
                _total_hard_bounces_seeded_key(mocked_service_id), bounce_epoch, bounce_count
            )
            mocked_bounce_rate_client._redis_client.expire.assert_called_with(
                _total_hard_bounces_seeded_key(mocked_service_id), 60 * 60 * 24
            )

    def test_set_total_notifications_seeded(self, mocked_bounce_rate_client, mocked_service_id):
        current_time = datetime.datetime.now()
        bounce_epoch = current_time.replace(minute=0, second=0, microsecond=0).timestamp()
        mocked_bounce_rate_client.set_total_notifications_seeded(mocked_service_id, current_time, 20)
        mocked_bounce_rate_client._redis_client.add_key_to_sorted_set.assert_called_with(
            _total_notifications_seeded_key(mocked_service_id), bounce_epoch, 20
        )
        mocked_bounce_rate_client._redis_client.expire.assert_called_with(
            _total_notifications_seeded_key(mocked_service_id), 60 * 60 * 24
        )
