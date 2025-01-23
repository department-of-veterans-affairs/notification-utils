import json
import logging as builtin_logging
import os
import uuid

import pytest
from pythonjsonlogger.json import JsonFormatter

from notifications_utils import logging


class App:
    def __init__(self, config=None, debug=False):
        self.config = config or {}
        self.debug = debug


@pytest.fixture(autouse=True)
def app(tmpdir, debug=True):
    return App(config={
        'NOTIFY_LOG_PATH': str(tmpdir / 'foo'),
        'NOTIFY_APP_NAME': 'bar',
        'NOTIFY_LOG_LEVEL': 'DEBUG',
    }, debug=debug)


@pytest.fixture(autouse=True)
def reset_environment():
    original_env = os.environ.get('NOTIFY_ENVIRONMENT', None)
    yield
    if original_env is not None:
        os.environ['NOTIFY_ENVIRONMENT'] = original_env
    else:
        os.environ.pop('NOTIFY_ENVIRONMENT', None)


def test_should_build_complete_log_line():
    service_id = uuid.uuid4()
    extra_fields = {
        'method': "method",
        'url': "url",
        'status': 200,
        'time_taken': "time_taken",
        'service_id': service_id,
    }
    assert logging.build_log_line(extra_fields) == \
        "{service_id} method url 200 time_taken".format(service_id=str(service_id))


def test_should_build_complete_log_line_ignoring_missing_fields():
    service_id = uuid.uuid4()
    extra_fields = {
        'method': "method",
        'status': 200,
        'time_taken': "time_taken",
        'service_id': service_id,
    }
    assert logging.build_log_line(extra_fields) == \
        "{service_id} method 200 time_taken".format(service_id=str(service_id))


def test_should_build_log_line_without_service_id():
    extra_fields = {
        'method': "method",
        'url': "url",
        'status': 200,
        'time_taken': "time_taken",
    }
    assert logging.build_log_line(extra_fields) == "method url 200 time_taken"


def test_should_build_log_line_without_service_id_or_time_taken():
    extra_fields = {
        'method': "method",
        'url': "url",
        'status': 200,
    }
    assert logging.build_log_line(extra_fields) == "method url 200"


def test_should_build_complete_statsd_line():
    service_id = uuid.uuid4()
    extra_fields = {
        'method': "method",
        'endpoint': "endpoint",
        'status': 200,
        'service_id': service_id,
    }
    assert logging.build_statsd_line(extra_fields) == \
        "service-id.{service_id}.method.endpoint.200".format(service_id=str(service_id))


def test_should_build_complete_statsd_line_without_service_id_prefix_for_admin_api_calls():
    extra_fields = {
        'method': "method",
        'endpoint': "endpoint",
        'status': 200,
        'service_id': 'notify-admin'
    }
    assert logging.build_statsd_line(extra_fields) == "notify-admin.method.endpoint.200"


def test_should_build_complete_statsd_line_ignoring_missing_fields():
    service_id = uuid.uuid4()
    extra_fields = {
        'method': "method",
        'endpoint': "endpoint",
        'service_id': service_id
    }
    assert logging.build_statsd_line(extra_fields) == \
        "service-id.{service_id}.method.endpoint".format(service_id=str(service_id))


def test_should_build_statsd_line_without_service_id_or_time_taken():
    extra_fields = {
        'method': "method",
        'endpoint': "endpoint",
        'status': 200,
    }
    assert logging.build_statsd_line(extra_fields) == "method.endpoint.200"


@pytest.mark.parametrize('app_name', ('notification-api', 'celery', None))
def test_get_handler_sets_up_logging_appropriately_with_debug(tmpdir, app, app_name):
    del app.config['NOTIFY_LOG_PATH']
    app.name = app_name
    app.debug = True
    handler = logging.get_handler(app)

    assert type(handler) is builtin_logging.StreamHandler
    assert type(handler.formatter) is JsonFormatter
    assert not (tmpdir / 'foo').exists()

    record = builtin_logging.makeLogRecord({
        "application": app.name,
        "args": ("Cornelius", 42),
        "levelname": "debug",
        "lineno": 1999,
        "msg": "Hello, %s.  Line %d.",
        "pathname": "the_path",
        "requestId": "id",
    })
    message = json.loads(handler.formatter.format(record))
    assert message['application'] == app_name
    assert message['levelname'] == 'debug'
    assert message['requestId'] == 'id'
    assert message['message'] == 'Hello, Cornelius.  Line 42.'
    assert message['pathname'] == 'the_path'
    assert message['lineno'] == 1999


@pytest.mark.parametrize('app_name', ('notification-api', 'celery', None))
def test_get_handler_sets_up_logging_appropriately_without_debug(app, app_name):
    app.name = app_name
    app.debug = False
    handler = logging.get_handler(app)
    assert type(handler) is builtin_logging.StreamHandler
    assert type(handler.formatter) is JsonFormatter

    record = builtin_logging.makeLogRecord({
        "application": app.name,
        "args": ("Cornelius", 42),
        "levelname": "debug",
        "lineno": 1999,
        "msg": "Hello, %s.  Line %d.",
        "pathname": "the_path",
        "requestId": "id",
    })
    message = handler.formatter.format(record)
    message_dict = json.loads(message)
    assert "asctime" in message_dict
    assert message_dict["application"] == app_name or 'test'
    assert message_dict["levelname"] == "debug"
    assert message_dict["requestId"] == "id"
    assert message_dict["message"] == "Hello, Cornelius.  Line 42."
    assert message_dict["pathname"] == "the_path"
    assert message_dict["lineno"] == 1999


def test_it_set_log_level_production(app, reset_environment):
    del app.config['NOTIFY_LOG_LEVEL']

    os.environ['NOTIFY_ENVIRONMENT'] = 'production'
    logging.set_log_level(app)
    assert app.config['NOTIFY_LOG_LEVEL'] == 'INFO'


def test_it_set_log_level_non_production(app, reset_environment):
    os.environ['NOTIFY_ENVIRONMENT'] = 'development'
    logging.set_log_level(app)
    assert app.config['NOTIFY_LOG_LEVEL'] == 'DEBUG'
