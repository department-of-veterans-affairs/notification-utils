import json
import logging as builtin_logging
import uuid
from notifications_utils import logging
from pythonjsonlogger.jsonlogger import JsonFormatter


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


def test_get_handler_sets_up_logging_appropriately_with_debug(tmpdir):
    class App:
        config = {
            'NOTIFY_LOG_PATH': str(tmpdir / 'foo'),
            'NOTIFY_APP_NAME': 'bar',
            'NOTIFY_LOG_LEVEL': 'ERROR'
        }
        debug = True

    app = App()

    handler = logging.get_handler(app)

    assert type(handler) == builtin_logging.StreamHandler
    assert type(handler.formatter) == builtin_logging.Formatter
    assert not (tmpdir / 'foo').exists()

    application = app.config["NOTIFY_APP_NAME"]
    record = builtin_logging.makeLogRecord({
        "application": application,
        "args": ("Cornelius", 42),
        "levelname": "debug",
        "lineno": 1999,
        "msg": "Hello, %s.  Line %d.",
        "name": "the_name",
        "pathname": "the_path",
        "requestId": "id",
    })
    message = handler.formatter.format(record)
    assert message.endswith(f' {application} the_name debug id "Hello, Cornelius.  Line 42." [in the_path:1999]')


def test_get_handler_sets_up_logging_appropriately_without_debug(tmpdir):
    class App:
        config = {
            # make a tempfile called foo
            'NOTIFY_LOG_PATH': str(tmpdir / 'foo'),
            'NOTIFY_APP_NAME': 'bar',
            'NOTIFY_LOG_LEVEL': 'ERROR'
        }
        debug = False

    app = App()
    handler = logging.get_handler(app)
    assert type(handler) == builtin_logging.StreamHandler
    assert type(handler.formatter) == JsonFormatter

    application = app.config["NOTIFY_APP_NAME"]
    record = builtin_logging.makeLogRecord({
        "application": application,
        "args": ("Cornelius", 42),
        "levelname": "debug",
        "lineno": 1999,
        "msg": "Hello, %s.  Line %d.",
        "name": "the_name",
        "pathname": "the_path",
        "requestId": "id",
    })
    message = handler.formatter.format(record)
    message_dict = json.loads(message)
    assert "asctime" in message_dict
    assert message_dict["application"] == application
    assert message_dict["name"] == "the_name"
    assert message_dict["levelname"] == "debug"
    assert message_dict["requestId"] == "id"
    assert message_dict["message"] == "Hello, Cornelius.  Line 42."
    assert message_dict["pathname"] == "the_path"
    assert message_dict["lineno"] == 1999
