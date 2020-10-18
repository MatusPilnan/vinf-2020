import datetime


def measure_execution_time(enabled):
    def execution_time(func):
        def wrapper(*args, **kwargs):
            start = None
            if enabled:
                start = datetime.datetime.now()
            result = func(*args, **kwargs)
            if start:
                print(f'{func.__name__}() took {datetime.datetime.now() - start}')
            return result

        wrapper.__doc__ = func.__doc__
        wrapper.__name__ = func.__name__
        return wrapper

    return execution_time
