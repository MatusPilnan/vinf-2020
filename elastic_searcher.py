import argparse

import pandas as pd
from elasticsearch import Elasticsearch

from common import MAIN_LANGS


def build_query(term, source, target, reverse=False):
    field = "original_title"
    if source not in MAIN_LANGS or reverse:
        field = "translated"
        source, target = (target, source)

    return {
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            field: {
                                "query": term
                            }
                        }
                    },
                    {
                        "match": {
                            "source_lang": {
                                "query": source
                            }
                        }
                    },
                    {
                        "match": {
                            "target_lang": {
                                "query": target
                            }
                        }
                    }
                ]
            }
        }
    }


def translate(term, source, target):
    es = Elasticsearch(retry_on_timeout=True, timeout=120)
    result_columns = [f'title_{source}', f'title_{target}']
    if source in MAIN_LANGS:
        query = build_query(term, source, target)
    elif target in MAIN_LANGS:
        query = build_query(term, source, target, reverse=True)
        result_columns = [f'title_{target}', f'title_{source}']
    else:
        raise ValueError(f"Translation for {term} from {source} to {target} not found")

    results = es.search(index='vinf', body=query)
    results = list(map(lambda r: r['_source'], results['hits']['hits']))

    if not results:
        query = build_query(term, source, target, reverse=True)
        results = es.search(index='vinf', body=query)
        results = list(map(lambda r: r['_source'], results['hits']['hits']))
        result_columns = [f'title_{target}', f'title_{source}']

    if not results:
        raise ValueError(f"Translation for {term} from {source} to {target} not found")
    results = pd.DataFrame().from_records(results)
    results = results.drop(columns=['source_lang', 'target_lang'])
    results.columns = result_columns
    return results.reindex(columns=[f'title_{source}', f'title_{target}'])


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Find a translation')
    arg_parser.add_argument('input', help='Input term to be translated')
    arg_parser.add_argument('lang_from', help='Language of the input')
    arg_parser.add_argument('lang_to', help='Code of target language')

    args = arg_parser.parse_args()

    print(translate(args.input, args.lang_from, args.lang_to))
