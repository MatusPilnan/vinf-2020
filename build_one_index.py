import datetime
from multiprocessing import Pool
from typing import Tuple

import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import parallel_bulk
from tqdm import tqdm
from whoosh.index import create_in

from common import INDEX_DIR, one_index_schema


def combinations(primary, secondary):
    for p in primary:
        for s in secondary:
            if p is not s:
                yield p, s


def process_lang_combination(languages: Tuple[str, str]):
    if not languages:
        return [], languages
    lang_from, lang_to = languages
    try:
        df_to = pd.read_csv(f'csv/langlinks/{lang_from}/to_{lang_to}.csv', sep='\t', header=None, index_col=0,
                            na_filter=False)
        df_from = pd.read_csv(f'csv/page/{lang_from}.csv', sep='\t', header=None, index_col=0)
        df = df_from.join(df_to, how='inner', rsuffix='_to_')
        df.columns = ['original_title', 'translated']
        df['original_title'] = df['original_title'].apply(lambda x: str(x).replace('_', ' '))
        df['source_lang'] = lang_from
        df['target_lang'] = lang_to
        return df.to_dict('records'), languages
    except FileNotFoundError:
        print(f'Translation not found: {languages}')
        return [], languages


def build_one_index(primary_languages, secondary_languages):
    i, j = 0, 0
    total_start = datetime.datetime.now()
    index = create_in(INDEX_DIR, one_index_schema, indexname='big_index')
    for records, langs in map(process_lang_combination, combinations(primary_languages, secondary_languages)):
        writer = index.writer(limitmb=2048, procs=4)
        i += 1
        for r in tqdm(records, desc=f'{i} of {len(primary_languages) * len(secondary_languages)} - {langs}'):
            writer.add_document(**r)

        print(f'Committing writer: {langs}')
        start = datetime.datetime.now()
        writer.commit()
        print(f'Writer committed ({datetime.datetime.now() - start})')
        print(f'Time taken so far: {datetime.datetime.now() - total_start}')
    print(i)


def build_elastic_index(primary_languages, secondary_languages):
    secondary_languages.sort()
    es = Elasticsearch(retry_on_timeout=True, timeout=120)
    if es.indices.exists('vinf'):
        es.indices.delete('vinf')
    es.indices.create(index='vinf', body={
        "settings": {
            "number_of_shards": 3,
            "number_of_replicas": 0,
            "refresh_interval": -1,
            "analysis": {
                "analyzer": {
                    "default": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "asciifolding"
                        ]
                    }
                }
            }
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "original_title": {
                    "type": "text"
                },
                "source_lang": {
                    "type": "keyword"
                },
                "target_lang": {
                    "type": "keyword"
                },
                "translated": {
                    "type": "text"
                }
            }
        }
    })

    def actions():
        pool = Pool(4)
        i = 0
        for records, langs in pool.imap_unordered(process_lang_combination,
                                                  combinations(primary_languages, secondary_languages)):
            i += 1
            for action in tqdm(map(lambda r: {"_index": "vinf", "_source": r}, records),
                               desc=f'{i} of {len(primary_languages) * len(secondary_languages)} - {langs}'):
                if action:
                    yield action

    try:
        for success, result in parallel_bulk(client=es,
                                             actions=actions(),
                                             chunk_size=50000):
            if not success:
                print(result)
    finally:
        es.indices.put_settings(body={"index": {"refresh_interval": None}}, index='vinf')


if __name__ == '__main__':
    build_one_index(['sk'], ['fi'])
