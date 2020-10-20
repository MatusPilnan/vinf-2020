from whoosh.analysis import StandardAnalyzer, CharsetFilter
from whoosh.fields import *
from whoosh.support.charset import accent_map

INDEX_DIR = 'indexdir'
PAGE_IDX_NAME = 'page_idx'
MAIN_LANGS = ['cs', 'fi', 'sk']

analyzer = StandardAnalyzer() | CharsetFilter(accent_map)
page_schema = Schema(id=NUMERIC(stored=True), title=TEXT(stored=True, analyzer=analyzer))


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


def index_name(lang):
    return f'{lang}_{PAGE_IDX_NAME}'
