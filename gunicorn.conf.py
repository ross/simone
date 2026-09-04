# We intentionally do NOT run with --preload. `simone.urls` starts a
# singleton Cron background thread (and opens a DB connection) as an import
# side effect (see wsgi.py's `cron.start()`), and --preload would run that
# in the gunicorn master before workers are forked. fork() then duplicates
# whatever the Cron thread has in flight (its DB connection, mid-transaction
# or not) into the worker, which can leave things like table locks stuck
# open with nothing left to ever commit/release them -- every request that
# then needs the same rows hangs forever with nothing logged, until the
# client (Slack, ~3s) gives up. Without --preload, each worker loads the app
# (and starts its own Cron thread) fully independently, post-fork, so there
# is nothing shared to corrupt.
#
# This relies on running a single worker: script/run doesn't pass --workers,
# so gunicorn defaults to one. If that's ever increased, Cron would start
# once per worker and tick (and message Slack) that many times over.

import os

# Set here, not left to simone/wsgi.py's own setdefault: post_fork below calls
# DjangoInstrumentor().instrument(), which reads Django settings itself (to find
# MIDDLEWARE etc.), and gunicorn runs post_fork *before* the worker imports
# simone.wsgi. If DJANGO_SETTINGS_MODULE isn't set by then, Django's lazy
# settings object configures itself from global_settings -- and once that's
# happened, wsgi.py's later get_wsgi_application() never loads simone.settings
# at all (LazySettings only consults the env var the first time it's forced to
# configure). Every request then 500s with AttributeError on ROOT_URLCONF.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simone.settings')


def worker_abort(worker):
    '''
    Called when the arbiter SIGABRTs a worker for failing to heartbeat
    within --timeout. Dump every thread's stack so a hang shows up in the
    logs instead of just a silent restart.
    '''
    import faulthandler
    import sys

    faulthandler.dump_traceback(file=sys.stderr)


def post_fork(server, worker):
    '''
    Wire OpenTelemetry tracing into each worker.

    Done here rather than at import time (or via the `opentelemetry-instrument`
    CLI wrapper) for the same reason the module comment above gives for not
    using --preload, plus one of its own: BatchSpanProcessor owns a background
    export thread, and a thread does not survive fork() -- only the forking
    thread's state does. A TracerProvider built in the master would leave every
    worker holding a processor whose export thread only ever existed in the
    parent, silently exporting nothing. post_fork runs inside each freshly
    forked worker, before it imports simone.wsgi, so DjangoInstrumentor is in
    place before Django's own URL resolution and middleware load.

    Spans go straight to Tempo's OTLP/HTTP receiver (OTEL_EXPORTER_OTLP_ENDPOINT
    in the compose environment), not through logit -- there is nothing logit
    would add to spans an SDK already produced. Each one is a child of the span
    logit lifts from nginx's access log line for the same request: nginx sets a
    traceparent header and the default W3C propagator picks it up here with no
    code of our own.

    A no-op when OTEL_EXPORTER_OTLP_ENDPOINT is unset, so running outside the
    compose stack (script/run directly, the dev docker-compose.yml) doesn't
    need a collector listening or spend every request's teardown waiting on a
    connection refused.
    '''
    if not os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT'):
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # service.name is what lets Tempo resolve a root service for these spans,
    # matching the `set` component logit stamps onto nginx's own.
    resource = Resource.create(
        {
            'service.name': os.environ.get('OTEL_SERVICE_NAME', 'simone'),
            'service.namespace': 'xormedia',
        }
    )
    provider = TracerProvider(resource=resource)
    # The exporter reads OTEL_EXPORTER_OTLP_ENDPOINT itself and appends
    # /v1/traces per the OTLP spec. This package only speaks protobuf, which
    # Tempo's receiver accepts natively.
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()
    # Puts the active trace/span id into every log record, so a log line can be
    # matched back to the trace it happened in.
    LoggingInstrumentor().instrument(set_logging_format=True)
