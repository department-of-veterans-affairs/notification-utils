# from unittest.mock import Mock

import pytest
from datetime import datetime, timedelta
from notifications_utils.clients.statsd.statsd_client import StatsdClient


@pytest.fixture(scope='function')
def enabled_statsd_client(app, mocker):
    app.config['STATSD_ENABLED'] = True
    return build_statsd_client(app, mocker)


@pytest.fixture(scope='function')
def disabled_statsd_client(app, mocker):
    app.config['STATSD_ENABLED'] = False
    return build_statsd_client(app, mocker)


@pytest.fixture
def mock_dogstatsd(mocker):
    return mocker.patch('notifications_utils.clients.statsd.statsd_client.statsd')


def build_statsd_client(app, mocker):
    client = StatsdClient()
    app.config['NOTIFY_ENVIRONMENT'] = "test"
    app.config['NOTIFY_APP_NAME'] = "api"
    app.config['STATSD_HOST'] = "localhost"
    app.config['STATSD_PORT'] = "8000"
    app.config['STATSD_PREFIX'] = "prefix"
    client.init_app(app)
    # if not app.config['STATSD_ENABLED']:
    #     # statsd_client not initialised if statsd not enabled, so lets mock it
    #     client.statsd_client = Mock()
    return client


def test_should_create_correctly_formatted_namespace(enabled_statsd_client):
    assert enabled_statsd_client.format_stat_name("test") == "test.notifications.api.test"


def test_should_not_call_incr_if_not_enabled(disabled_statsd_client, mock_dogstatsd):
    disabled_statsd_client.incr('key')
    mock_dogstatsd.incr.assert_not_called()


def test_should_call_incr_if_enabled(enabled_statsd_client, mock_dogstatsd):
    enabled_statsd_client.incr('key')
    mock_dogstatsd.increment.assert_called_with('test.notifications.api.key', value=1, sample_rate=1, tags=None)


def test_should_call_incr_with_params_if_enabled(enabled_statsd_client, mock_dogstatsd):
    enabled_statsd_client.incr('key', 10, 11)
    mock_dogstatsd.increment.assert_called_with('test.notifications.api.key', value=10, sample_rate=11, tags=None)


def test_should_not_call_timing_if_not_enabled(disabled_statsd_client, mock_dogstatsd):
    disabled_statsd_client.timing('key', 1000)
    mock_dogstatsd.histogram.assert_not_called()


def test_should_call_timing_if_enabled(enabled_statsd_client, mock_dogstatsd):
    enabled_statsd_client.timing('key', 1000)
    mock_dogstatsd.histogram.assert_called_with('test.notifications.api.key', value=1000, sample_rate=1, tags=None)


def test_should_call_timing_with_params_if_enabled(enabled_statsd_client, mock_dogstatsd):
    enabled_statsd_client.timing('key', 1000, 99)
    mock_dogstatsd.histogram.assert_called_with('test.notifications.api.key', value=1000, sample_rate=99, tags=None)


def test_should_not_call_timing_from_dates_method_if_not_enabled(disabled_statsd_client, mock_dogstatsd):
    disabled_statsd_client.timing_with_dates('key', datetime.utcnow(), datetime.utcnow())
    mock_dogstatsd.histogram.assert_not_called()


def test_should_call_timing_from_dates_method_if_enabled(enabled_statsd_client, mock_dogstatsd):
    now = datetime.utcnow()
    enabled_statsd_client.timing_with_dates('key', now + timedelta(seconds=3), now)
    mock_dogstatsd.histogram.assert_called_with('test.notifications.api.key', value=3, sample_rate=1, tags=None)


def test_should_call_timing_from_dates_method_with_params_if_enabled(enabled_statsd_client, mock_dogstatsd):
    now = datetime.utcnow()
    enabled_statsd_client.timing_with_dates('key', now + timedelta(seconds=3), now, 99)
    mock_dogstatsd.histogram.assert_called_with('test.notifications.api.key', value=3, sample_rate=99, tags=None)


def test_should_not_call_gauge_if_not_enabled(disabled_statsd_client, mock_dogstatsd):
    disabled_statsd_client.gauge('key', 10)
    mock_dogstatsd.gauge.assert_not_called()


def test_should_call_gauge_if_enabled(enabled_statsd_client, mock_dogstatsd):
    enabled_statsd_client.gauge('key', 100)
    mock_dogstatsd.gauge.assert_called_with('test.notifications.api.key', 100, tags=None)
