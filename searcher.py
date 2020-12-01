import argparse
import os

import pandas as pd
from whoosh import index
from whoosh.qparser import QueryParser

import elastic_searcher
from common import measure_execution_time, INDEX_DIR, PAGE_IDX_NAME, page_schema, MAIN_LANGS, index_name

timer_enabled = False
args = None
if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Find a translation')
    arg_parser.add_argument('input', help='Input term to be translated')
    arg_parser.add_argument('lang_from',
                            help=f'Language code of the input. Should be one of {MAIN_LANGS} unless "-e" is also specified.')
    arg_parser.add_argument('lang_to', help='Code of target language')
    arg_parser.add_argument('-n', '--namespaces', help='Leave translated pages with namespace prefixes in output',
                            action='store_true')
    arg_parser.add_argument('-t', '--time', help='Whether to time the execution', action='store_true')
    arg_parser.add_argument('-e', '--elastic', help='Use Elasticsearch index', action='store_true')
    arg_parser.add_argument('--show_not_found', action='store_true', help='Show a list of pages that could not be '
                                                                          'translated')

    args = arg_parser.parse_args()
    timer_enabled = args.time


@measure_execution_time(timer_enabled)
def load_index(name):
    """
    Loads the Whoosh index

    :param name: Name of the index to load
    """
    return index.open_dir(INDEX_DIR, name)


@measure_execution_time(timer_enabled)
def translate(input_title, lang_from, lang_to, page_index=None):
    """
    Finds the translated title of input page title. Input title doesn't have to be a whole title.
    :param input_title: Title to translate
    :param lang_from: Language of input
    :param lang_to: Desired language
    :param page_index: Whoosh index to use
    :return: pd.DataFrame with original titles and translations
    """
    if not page_index:
        page_index = load_index(PAGE_IDX_NAME)
    check_target_lang(lang_from, lang_to)
    title = preprocess(input_title)
    pages = []
    try:
        pages = find_page_id(title, page_index)
    except ValueError as e:
        exit(f'Page {input_title} not found in {lang_from}wiki.\n{e}')
    translation = find_translated_title(pages, lang_from, lang_to)
    return translation


@measure_execution_time(timer_enabled)
def check_target_lang(source, target):
    """
    Checks if translation from `source` to `target` is possible.
    :param source: Language code of input
    :param target: Desirted language
    :return: True if OK
    """
    if os.path.exists(f'csv/langlinks/{source}/to_{target}.csv'):
        return True
    exit(f'Cannot translate from {source} to {target}. Check language codes and make sure parser has been run.')


@measure_execution_time(timer_enabled)
def preprocess(input_title: str):
    """
    Preprocesses user input by making it lowercase. Rest is done by Whoosh searcher.
    :param input_title:
    :return: Lowercased input
    """
    return input_title.lower()


@measure_execution_time(timer_enabled)
def find_page_id(title, idx):
    """
    Looks up page ID using Whoosh index. Title is lowercased, tokenized and accents are removed.
    Capable of finding pages which contain the input (doesn't have to be exact match)

    :param title: Page title (or part of title) to look up
    :param idx: The Whoosh index to use
    :return: List of (page_id, page_title) tuples
    """
    with idx.searcher() as searcher:
        parser = QueryParser('title', schema=page_schema)
        # Parse title into query using analyzer in index schema (tokenize, lowercase, remove accents)
        # Tokens are joined with AND
        results = searcher.search(parser.parse(title))
        if not results:
            # If no matches were found, throw error with correction suggestions
            suggestion = searcher.correct_query(parser.parse(title), title)
            raise ValueError(f"Did you mean: {suggestion.string}?")
        return [tuple(r.values()) for r in results]


@measure_execution_time(timer_enabled)
def find_translated_title(pages, lang_from, lang_to):
    """
    Find translated titles by page IDs
    :param pages:  List of (page_id, page_title) tuples
    :param lang_from: Input language code
    :param lang_to: Target language code
    :return: pd.DataFrame containing original and translated titles
    """
    df = pd.read_csv(f'csv/langlinks/{lang_from}/to_{lang_to}.csv', sep='\t', header=None, index_col=0)
    matches = pd.DataFrame.from_records(pages, index=0)
    df.columns = ['title']
    # Left join - leaves pages with no translation in, but sets None in target language column
    result = matches.join(df).drop(columns=0)
    result.columns = [f'title_{lang_from}', f'title_{lang_to}']
    return result


def discard_namespace(row):
    """
    Removes namespace (like Category: from page title). Based around position of colon (:) in the translated title.
    Namespaces are not present in titles from the `pages` table, but are present in `langlinks`.
    Therefore, a namespaced page translation should have more colons than the original title.
    If that is the case, anything before the first colon in the translated title is discarded.

    :param row: A row of pd.Dataframe with original title [0] and translated title [1]
    :return: Modified row
    """
    if row.iloc[1].count(':') > row.iloc[0].count(':'):
        colon = row.iloc[1].find(':')
        if colon:
            row.iloc[1] = row.iloc[1][colon + 1:]
    return row


if __name__ == '__main__':
    results = None
    if args.elastic:
        try:
            results = elastic_searcher.translate(args.input, args.lang_from, args.lang_to)
        except ValueError as e:
            exit(e)
    else:
        if args.lang_from not in MAIN_LANGS:
            exit(f'lang_from should be one of {MAIN_LANGS} unless "-e" is also specified. It was: {args.lang_from}')
        page_idx = load_index(index_name(args.lang_from))
        results = translate(args.input, args.lang_from, args.lang_to, page_idx)
    # Save correctly translated entries
    good_matches = results.dropna()
    if not args.namespaces:
        # noinspection PyTypeChecker
        good_matches = good_matches.apply(discard_namespace, axis=1)
        # Namespace removal can leave duplicate translations
        good_matches = good_matches.drop_duplicates()
    results = results.drop_duplicates([f'title_{args.lang_from}'])
    not_found = results[results[f'title_{args.lang_to}'].isna()][f'title_{args.lang_from}']
    if len(good_matches) > 1:
        print('Multiple translations found:')
    for row in good_matches.values:
        print(f'{row[0]} -> {row[1]}')

    if (args.show_not_found or len(good_matches) == 0) and len(not_found) > 0:
        print(f'Pages from {args.lang_from}wiki with no translation in {args.lang_to}wiki: {list(not_found)}')
