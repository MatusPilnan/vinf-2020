import argparse
import os

import pandas as pd
from unidecode import unidecode

from common import measure_execution_time

timer_enabled = False
args = None
if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Find a translation')
    arg_parser.add_argument('input', help='Input term to be translated')
    arg_parser.add_argument('lang_from', choices=['cs', 'fi', 'sk'], help='Language of the input')
    arg_parser.add_argument('lang_to', help='Code of target language')
    arg_parser.add_argument('-t', '--time', help='Whether to time the execution', action='store_true')

    args = arg_parser.parse_args()
    timer_enabled = args.time


@measure_execution_time(timer_enabled)
def translate(input, lang_from, lang_to):
    check_target_lang(lang_from, lang_to)
    title = preprocess(input)
    page_id, real_title = None, None
    try:
        page_id, real_title = find_page_id(title, lang_from)
    except TypeError:
        exit(f'Page {input} not found in {lang_from}wiki.')
    try:
        translation = find_translated_title(page_id, lang_from, lang_to)
        return translation
    except KeyError:
        exit(f'Page {real_title.replace("_", " ")} ({lang_from}, ID: {page_id}) not found in language {lang_to}')


@measure_execution_time(timer_enabled)
def check_target_lang(source, target):
    if os.path.exists(f'csv/langlinks/{source}/to_{target}.csv'):
        return True
    exit(f'Cannot translate from {source} to {target}. Check language codes and make sure parser has been run.')


@measure_execution_time(timer_enabled)
def preprocess(input: str):
    return input.replace(' ', '_').lower()


@measure_execution_time(timer_enabled)
def find_page_id(title, lang_from):
    df = pd.read_csv(f'csv/page/{lang_from}.csv', sep='\t', header=None, na_filter=False)
    df.columns = ['id', 'title']
    result = df[df['title'].str.lower() == title].values
    if result.size == 0:
        result = df[df['title'].apply(unidecode).str.lower() == unidecode(title)].values
    try:
        result = tuple(result[0])
    except IndexError:
        result = None
    return result


@measure_execution_time(timer_enabled)
def find_translated_title(page_id, lang_from, lang_to):
    df = pd.read_csv(f'csv/langlinks/{lang_from}/to_{lang_to}.csv', sep='\t', header=None, index_col=0)
    df.columns = ['title']
    result = df.at[page_id, 'title']
    return result


if __name__ == '__main__':
    print(translate(args.input, args.lang_from, args.lang_to))
