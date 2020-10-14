import argparse
import os
import time

import pandas as pd


def translate(input, lang_from, lang_to):
    check_target_lang(lang_from, lang_to)
    title = preprocess(input)
    page_id = find_page_id(title, lang_from)
    if not page_id:
        exit(f'Page {title} not found in {lang_from}wiki.')
    translation = find_translated_title(page_id, lang_from, lang_to)
    return translation


def check_target_lang(source, target):
    if os.path.exists(f'csv/langlinks/{source}/to_{target}.csv'):
        return True
    exit(f'Cannot translate from {source} to {target}. Check language codes and make sure parser has been run.')


def preprocess(input):
    return input


def find_page_id(title, lang_from):
    df = pd.read_csv(f'csv/page/{lang_from}.csv', sep='\t', header=None)
    df.columns = ['id', 'title']
    result = df[df['title'] == title]['id'].values[0]
    return result


def find_translated_title(page_id, lang_from, lang_to):
    df = pd.read_csv(f'csv/langlinks/{lang_from}/to_{lang_to}.csv', sep='\t', header=None, index_col=0)
    df.columns = ['title']
    result = df.at[page_id, 'title']
    return result


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Find a translation')
    arg_parser.add_argument('input', help='Input term to be translated')
    arg_parser.add_argument('lang_from', choices=['cs', 'fi', 'sk'], help='Language of the input')
    arg_parser.add_argument('lang_to', help='Code of target language')
    arg_parser.add_argument('-t', '--time', help='Whether to time the execution', action='store_true')

    args = arg_parser.parse_args()
    start = None
    if args.time:
        print('Starting...')
        start = time.time()
    print(translate(args.input, args.lang_from, args.lang_to))
    if start:
        print(f'Lookup took {time.time()-start} s')
