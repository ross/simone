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
    forked worker, before it imports simone.wsgi, so the instrumentation is in
    place before Django's own machinery loads -- and, for the DB spans, before
    Django opens its first connection.

    The setup itself lives in simone/tracing.py so the management commands and
    a dev server can opt in the same way. It's a no-op when
    OTEL_EXPORTER_OTLP_ENDPOINT is unset.
    '''
    from simone.tracing import configure_tracing

    configure_tracing()
