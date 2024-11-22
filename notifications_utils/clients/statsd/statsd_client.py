from statsd.client.base import StatsClientBase
from socket import socket, AF_INET, SOCK_DGRAM
from flask import current_app


class NotifyStatsClient(StatsClientBase):
    def __init__(self, host, port, prefix):
        self._host = host
        self._port = port
        self._prefix = prefix
        self._sock = socket(AF_INET, SOCK_DGRAM)

    def _send(self, data):
        try:
            self._sock.sendto(data.encode('ascii'), (self._host, self._port))
        except Exception as e:
            current_app.logger.warning('Error sending statsd metric: {}'.format(str(e)))
            pass


class StatsdClient():
    def __init__(self):
        self.statsd_client = None

    def init_app(self, app, *args, **kwargs):
        app.statsd_client = self
        self.active = app.config.get('STATSD_ENABLED')
        self.namespace = "{}.notifications.{}.".format(
            app.config.get('NOTIFY_ENVIRONMENT'),
            app.config.get('NOTIFY_APP_NAME')
        )

        if self.active:
            self.statsd_client = NotifyStatsClient(
                app.config.get('STATSD_HOST'),
                app.config.get('STATSD_PORT'),
                prefix=app.config.get('STATSD_PREFIX')
            )

    def format_stat_name(self, stat):
        return self.namespace + stat

    def incr(self, stat, count=1, rate=1):
        if self.active:
            self.statsd_client.incr(self.format_stat_name(stat), count, rate)

    def gauge(self, stat, count):
        if self.active:
            self.statsd_client.gauge(self.format_stat_name(stat), count)

    def histogram(self, stat, value, rate=1):
        """Histogram is a DataDog specific metric type, which we've added here to our statsd client. StatsD packets
        are strings with this format - <metric_name>:<value>|<type>|@<sample_rate>.
        For a histogram, the metric type is 'h'.

        statsd _send_stat reference: https://github.com/jsocol/pystatsd/blob/master/statsd/client/base.py#L60
        dogstasd histogram reference: https://github.com/DataDog/datadogpy/blob/master/datadog/dogstatsd/base.py#L950
        """
        if self.active:
            self.statsd_client._send_stat(self.format_stat_name(stat), '%s|h' % value, rate)

    def timing(self, stat, delta, rate=1):
        if self.active:
            self.statsd_client.timing(self.format_stat_name(stat), delta, rate)

    def timing_with_dates(self, stat, start, end, rate=1):
        if self.active:
            delta = (start - end).total_seconds()
            self.statsd_client.timing(self.format_stat_name(stat), delta, rate)
