'''
OpenTelemetry setup, in one place so anything that runs the app can opt in --
gunicorn (see gunicorn.conf.py's post_fork), the management commands, or a
dev server. Spans go to whatever OTEL_EXPORTER_OTLP_ENDPOINT names; in the
compose stack that's Grafana Tempo's OTLP/HTTP receiver.
'''

from logging import getLogger
from os import environ

log = getLogger('tracing')


def configure_tracing():
    '''
    Build a TracerProvider and install every instrumentor we use.

    A no-op when OTEL_EXPORTER_OTLP_ENDPOINT is unset, so running outside the
    compose stack doesn't need a collector listening or spend every request's
    teardown retrying a connection refused.

    WHERE this is called from matters, and isn't arbitrary:

      * The BatchSpanProcessor below owns a background export thread, and a
        thread does not survive fork(). Under gunicorn this has to run in the
        worker, post-fork, or the provider's exporter only ever exists in the
        master and nothing is ever sent.

      * trace_integration() patches mysql.connector.connect, so it only
        affects connections opened afterwards. Django opens its first
        connection when simone.wsgi is imported, which is after post_fork --
        so this is correct today, but it's the reason this can't drift into
        an AppConfig.ready() or a middleware later.

    Returns True if tracing was configured, False if it was skipped.
    '''
    if not environ.get('OTEL_EXPORTER_OTLP_ENDPOINT'):
        return False

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.dbapi import trace_integration
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.threading import ThreadingInstrumentor
    from opentelemetry.instrumentation.urllib import URLLibInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # service.name is what lets Tempo resolve a root service for these spans,
    # matching the `set` component logit stamps onto nginx's own.
    resource = Resource.create(
        {
            'service.name': environ.get('OTEL_SERVICE_NAME', 'simone'),
            'service.namespace': 'xormedia',
        }
    )
    provider = TracerProvider(resource=resource)
    # The exporter reads OTEL_EXPORTER_OTLP_ENDPOINT itself and appends
    # /v1/traces per the OTLP spec. This package only speaks protobuf, which
    # Tempo's receiver accepts natively.
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    # One SERVER span per request. Note it produces no DB spans of its own --
    # that's what trace_integration below is for.
    DjangoInstrumentor().instrument()
    # Puts the active trace/span id into every log record, so a log line can
    # be matched back to the trace it happened in.
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Outbound HTTP, which takes two instrumentors because the app makes its
    # calls two different ways:
    #   requests -- the shared Session in simone/handlers.py, used by every
    #     handler/chat API call (weather, jokes, quotes, images, stonks).
    #   urllib   -- slack_sdk's sync WebClient, which builds an OpenerDirector
    #     over urllib.request rather than using requests or urllib3. Every
    #     chat_postMessage/reactions_add/conversations_info goes through here,
    #     so without this the Slack egress on nearly every request is
    #     invisible.
    RequestsInstrumentor().instrument()
    URLLibInstrumentor().instrument()

    # Emits no telemetry itself; it propagates the active context into threads
    # and ThreadPoolExecutor workers. Load-bearing here: slack_bolt runs its
    # listeners on the executor in simone/dispatcher.py, so handler work
    # happens *after* the HTTP response is sent (Slack wants an ack in ~3s).
    # Without this every handler span would be an orphan root instead of a
    # child of the request that caused it. A child outliving its parent is
    # normal for async work and renders correctly in Tempo.
    #
    # It also covers the private ThreadPoolExecutor in handler/chat/stonks.py.
    # Cron opts back out explicitly -- see Cron.run in simone/dispatcher.py.
    ThreadingInstrumentor().instrument()

    # DB spans, via the dbapi instrumentation directly rather than
    # opentelemetry-instrumentation-mysql. That package is a single
    # wrap_connect call wearing a version bound of
    # "mysql-connector-python >= 8.0, < 10.0" -- we're on 26.x, so its
    # instrument() would raise DependencyConflict, log an error and return
    # WITHOUT instrumenting. It would look installed and quietly do nothing.
    # Calling the underlying function skips the bogus gate and a dependency.
    #
    # This reaches the ORM because mysql/connector/django/base.py does
    # `cnx = mysql.connector.connect(...)` -- a live module attribute lookup,
    # so the patch intercepts it and Django's connection is the traced proxy.
    #
    # Imported here rather than at module scope: dev settings fall back to
    # sqlite3 when SIMONE_DB_NAME is unset, and this shouldn't be a hard
    # requirement there.
    #
    # No enable_commenter: sqlcommenter rewrites each query with a unique
    # traceparent comment, which defeats statement caching, and upstream warns
    # it's pathological with prepared cursors.
    try:
        import mysql.connector

        trace_integration(mysql.connector, 'connect', 'mysql')
    except ImportError:
        log.info('configure_tracing: mysql.connector absent, no DB spans')

    return True
