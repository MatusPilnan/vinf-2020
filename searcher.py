import argparse
import os

import pandas as pd
from whoosh import index
from whoosh.qparser import QueryParser

from common import measure_execution_time, INDEX_DIR, PAGE_IDX_NAME, page_schema, MAIN_LANGS, index_name

timer_enabled = False
args = None
if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Find a translation')
    arg_parser.add_argument('input', help='Input term to be translated')
    arg_parser.add_argument('lang_from', choices=MAIN_LANGS, help='Language of the input')
    arg_parser.add_argument('lang_to', help='Code of target language')
    arg_parser.add_argument('-n', '--namespaces', help='Leave translated pages with namespace prefixes in output',
                            action='store_true')
    arg_parser.add_argument('-t', '--time', help='Whether to time the execution', action='store_true')
    arg_parser.add_argument('--show_not_found', action='store_true', help='Show a list of pages that could not be '
                                                                          'translated')

    args = arg_parser.parse_args()
    timer_enabled = args.time


@measure_execution_time(timer_enabled)
def load_index(name):
    return index.open_dir(INDEX_DIR, name)


@measure_execution_time(timer_enabled)
def translate(input_title, lang_from, lang_to, page_index=None):
    if not page_index:
        page_index = load_index(PAGE_IDX_NAME)
    check_target_lang(lang_from, lang_to)
    title = preprocess(input_title)
    pages = find_page_id(title, page_index)
    if not pages:
        exit(f'Page {input_title} not found in {lang_from}wiki.')
    translation = find_translated_title(pages, lang_from, lang_to)
    return translation


@measure_execution_time(timer_enabled)
def check_target_lang(source, target):
    if os.path.exists(f'csv/langlinks/{source}/to_{target}.csv'):
        return True
    exit(f'Cannot translate from {source} to {target}. Check language codes and make sure parser has been run.')


@measure_execution_time(timer_enabled)
def preprocess(input_title: str):
    return input_title.lower()


@measure_execution_time(timer_enabled)
def find_page_id(title, idx):
    with idx.searcher() as searcher:
        parser = QueryParser('title', schema=page_schema)
        results = searcher.search(parser.parse(title))
        return [tuple(r.values()) for r in results]


@measure_execution_time(timer_enabled)
def find_translated_title(pages, lang_from, lang_to):
    df = pd.read_csv(f'csv/langlinks/{lang_from}/to_{lang_to}.csv', sep='\t', header=None, index_col=0)
    matches = pd.DataFrame.from_records(pages, index=0)
    df.columns = ['title']
    result = matches.join(df).drop(columns=0)
    result.columns = [f'title_{lang_from}', f'title_{lang_to}']
    return result


def discard_namespace(row):
    if row.iloc[1].count(':') > row.iloc[0].count(':'):
        colon = row.iloc[1].find(':')
        if colon:
            row.iloc[1] = row.iloc[1][colon + 1:]
    return row


if __name__ == '__main__':
    page_idx = load_index(index_name(args.lang_from))
    results = translate(args.input, args.lang_from, args.lang_to, page_idx)
    good_matches = results.dropna()
    if not args.namespaces:
        # noinspection PyTypeChecker
        good_matches = good_matches.apply(discard_namespace, axis=1)
        good_matches = good_matches.drop_duplicates()
    results = results.drop_duplicates([f'title_{args.lang_from}'])
    not_found = results[results[f'title_{args.lang_to}'].isna()][f'title_{args.lang_from}']
    if len(good_matches) > 1:
        print('Multiple translations found:')
    for row in good_matches.values:
        print(f'{row[0]} -> {row[1]}')

    if (args.show_not_found or len(good_matches) == 0) and len(not_found) > 0:
        print(f'Pages from {args.lang_from}wiki with no translation in {args.lang_to}wiki: {list(not_found)}')
    # print(results)
