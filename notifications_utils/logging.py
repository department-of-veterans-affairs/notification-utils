import logging
import os
import sys
from itertools import product
from pathlib import Path
from time import monotonic
from uuid import uuid4

from flask import request, g
from flask.ctx import has_request_context
from pythonjsonlogger.jsonlogger import JsonFormatter


# The "application" and "requestId" fields are non-standard LogRecord attributes added below in the
# "get_handler" function via filters.  If this causes errors, logging is misconfigured.
#     https://docs.python.org/3.8/library/logging.html#logrecord-attributes
API_LOG_FORMAT = '%(asctime)s %(application)s %(levelname)s ' \
                 '%(requestId)s "%(message)s" [in %(pathname)s:%(lineno)d]'
CELERY_LOG_FORMAT = '%(asctime)s %(application)s %(processName)s %(levelname)s ' \
                    '%(requestId)s "%(message)s" [in %(pathname)s:%(lineno)d]'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

_service_map = {
    'app': 'notification-api',
    'delivery': 'celery',
}

logger = logging.getLogger(__name__)


def build_log_line(extra_fields):
    fields = []
    if 'service_id' in extra_fields:
        fields.append(str(extra_fields.get('service_id')))
    standard_fields = [extra_fields.get('method'), extra_fields.get('url'), extra_fields.get('status')]
    fields += [str(field) for field in standard_fields if field is not None]
    if 'time_taken' in extra_fields:
        fields.append(extra_fields.get('time_taken'))
    return ' '.join(fields)


def build_statsd_line(extra_fields):
    fields = []
    if 'service_id' in extra_fields:
        if extra_fields.get('service_id') == 'notify-admin':
            fields = [str(extra_fields.get('service_id'))]
        else:
            fields = ["service-id", str(extra_fields.get('service_id'))]
    standard_fields = [extra_fields.get('method'), extra_fields.get('endpoint'), extra_fields.get('status')]
    fields += [str(field) for field in standard_fields if field is not None]
    return '.'.join(fields)


def init_app(app, statsd_client=None):
    set_log_level(app)

    app.config.setdefault('NOTIFY_APP_NAME', 'none')
    app.config.setdefault('NOTIFY_LOG_PATH', './log/application.log')

    @app.after_request
    def after_request(response):
        extra_fields = {
            'method': request.method,
            'url': request.url,
            'status': response.status_code,
        }

        if 'service_id' in g:
            extra_fields['service_id'] = g.service_id

        if 'start' in g:
            time_taken = monotonic() - g.start
            extra_fields['time_taken'] = "%.5f" % time_taken

        if 'endpoint' in g:
            extra_fields['endpoint'] = g.endpoint

        if statsd_client:
            stat = build_statsd_line(extra_fields)
            app.logger.info(build_log_line(extra_fields))
            statsd_client.incr(stat)

            if 'time_taken' in extra_fields:
                statsd_client.timing(stat + '.elapsed_time', time_taken)

        return response

    logging.getLogger().addHandler(logging.NullHandler())

    del app.logger.handlers[:]

    ensure_log_path_exists(app.config['NOTIFY_LOG_PATH'])
    the_handler = get_handler(app)
    loglevel = logging.getLevelName(app.config['NOTIFY_LOG_LEVEL'])
    loggers = [app.logger, logging.getLogger('utils')]
    for the_logger, handler in product(loggers, [the_handler]):
        the_logger.addHandler(handler)
        the_logger.setLevel(loglevel)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('s3transfer').setLevel(logging.WARNING)

    app.logger.info("Logging configured. The log level has been set to %s", app.logger.level)


def set_log_level(app):
    """
    For production environment, set log level to INFO.
    For all other environment, set log level to DEBUG.
    """
    if os.environ['NOTIFY_ENVIRONMENT'] == 'production':
        app.config.setdefault('NOTIFY_LOG_LEVEL', 'INFO')
    else:
        app.config.setdefault('NOTIFY_LOG_LEVEL', 'DEBUG')


def ensure_log_path_exists(path):
    """
    This function assumes you're passing a path to a file and attempts to create
    the path leading to that file.
    """

    try:
        Path(path).parent.mkdir(mode=755, parents=True)
    except FileExistsError:
        # The path and file already exist, which is acceptable.
        pass


def is_200_static_log(log) -> bool:
    """ Turn off 200 OK static logs in development. """

    msg = log.getMessage()
    return not ('GET /static/' in msg and ' 200 ' in msg)


def get_handler(app):
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.getLevelName(app.config['NOTIFY_LOG_LEVEL']))
    stream_handler.addFilter(AppNameFilter(app.config['NOTIFY_APP_NAME']))
    stream_handler.addFilter(RequestIdFilter())

    if app.debug:
        # Human readable stdout logs that omit static route 200 responses
        logging.getLogger('werkzeug').addFilter(is_200_static_log)

    stream_handler.setFormatter(
        JsonFormatter(
            CELERY_LOG_FORMAT if _service_map.get(app.name, API_LOG_FORMAT) == 'celery' else API_LOG_FORMAT,
            TIME_FORMAT,
        )
    )

    return stream_handler


class AppNameFilter(logging.Filter):
    def __init__(self, app_name):
        self.service = _service_map.get(app_name, 'test')

    def filter(self, record):
        record.application = self.service
        return record


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        # The else is for celery
        if not getattr(record, 'requestId', ''):
            record.requestId = RequestIdFilter._get_api_id() if has_request_context() else 'no-request-id'
        return record

    @staticmethod
    def _get_api_id() -> str:
        """Generate a request_id.

        g is a Flask global for this request. It's attached to the Flask instance and is only persisted for that request
        """
        return g.request_id if getattr(g, 'request_id', '') else str(uuid4())
