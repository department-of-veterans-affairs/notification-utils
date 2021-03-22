from typing import List

from datadog import initialize, statsd


class StatsdClient():
    def init_app(self, app, *args, **kwargs):
        app.statsd_client = self
        self.active = app.config.get('STATSD_ENABLED')
        self.namespace = "{}.notifications.{}.".format(
            app.config.get('NOTIFY_ENVIRONMENT'),
            app.config.get('NOTIFY_APP_NAME')
        )

        if self.active:
            options = {
                'statsd_host': app.config.get('STATSD_HOST'),
                'statsd_port': app.config.get('STATSD_PORT'),
            }

            initialize(**options)

    def format_stat_name(self, stat):
        return self.namespace + stat

    def incr(self, stat, count=1, rate=1, tags: List[str] = None):
        if self.active:
            statsd.increment(self.format_stat_name(stat), value=count, sample_rate=rate, tags=tags)

    def gauge(self, stat, count, tags: List[str] = None):
        if self.active:
            statsd.gauge(self.format_stat_name(stat), count, tags=tags)

    def timing(self, stat, delta, rate=1, tags: List[str] = None):
        if self.active:
            statsd.histogram(self.format_stat_name(stat), value=delta, sample_rate=rate, tags=tags)

    def timing_with_dates(self, stat, start, end, rate=1, tags: List[str] = None):
        if self.active:
            delta = (start - end).total_seconds()
            statsd.histogram(self.format_stat_name(stat), value=delta, sample_rate=rate, tags=tags)
