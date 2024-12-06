from os import environ


def bench_profile(func):
    # inner1 is a Wrapper function in
    # which the argument is called

    # inner function can access the outer local
    # functions like in this case "func"
    def exec_profiler(*args, **kwargs):
        import cProfile
        import io
        import logging
        import pstats
        import resource
        from sys import platform

        def report_resource():
            if platform != 'win32':
                usage = resource.getrusage(resource.RUSAGE_SELF)
                RESOURCES = [
                    ('ru_utime', 'User time'),
                    ('ru_stime', 'System time'),
                    ('ru_maxrss', 'Max. Resident Set Size'),
                    ('ru_ixrss', 'Shared Memory Size'),
                    ('ru_idrss', 'Unshared Memory Size'),
                    ('ru_isrss', 'Stack Size'),
                    ('ru_inblock', 'Block inputs'),
                    ('ru_oublock', 'Block outputs')]
                logger.critical('Resource usage:')
                for name, desc in RESOURCES:
                    logger.critical('  {:<25} ({:<10}) = {}'.format(desc, name, getattr(usage, name)))

        logger = logging.getLogger(__name__)
        logger.addHandler(logging.StreamHandler())

        pr = cProfile.Profile()
        pr.enable()

        # run user code
        response = func(*args, **kwargs)

        pr.disable()
        s = io.StringIO()
        sortby = pstats.SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        logger.critical(s.getvalue())
        report_resource()
        return response

    def no_profiler(*args, **kwargs):
        response = func(*args, **kwargs)
        return response

    bench = environ.get('BENCH_PROFILE')
    print("bench profile->", bench)
    if bench:
        return exec_profiler
    else:
        return no_profiler
