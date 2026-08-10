def post_fork(server, worker):
    '''
    We run with --preload, so `simone.urls` (and the Cron thread it starts)
    is imported in the master process before workers are forked. Any
    database connection the master has opened by that point (e.g. Cron's
    first tick) gets duplicated into each worker via fork(), leaving the
    master and worker sharing one underlying socket. Once both sides use it
    concurrently they corrupt each other's protocol state and hang forever
    with no error logged. Dropping inherited connections here forces each
    worker to lazily open its own on first use instead.
    '''
    from django.db import connections

    connections.close_all()
