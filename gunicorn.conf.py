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


def worker_abort(worker):
    '''
    Called when the arbiter SIGABRTs a worker for failing to heartbeat
    within --timeout. Dump every thread's stack so a hang shows up in the
    logs instead of just a silent restart.
    '''
    import faulthandler
    import sys

    faulthandler.dump_traceback(file=sys.stderr)
