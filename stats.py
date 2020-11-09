import argparse
import json
from pprint import pprint

import pandas as pd
from whoosh import index

from common import MAIN_LANGS, INDEX_DIR, index_name


def available_langs():
    with open('info.json') as f:
        info = json.load(f)
        try:
            return info['allLangs']
        except KeyError:
            return []


def check_backlinks():
    for lang_from in MAIN_LANGS:
        for lang_to in MAIN_LANGS:
            if lang_to == lang_from:
                continue
            print(f'Checking backlinks {lang_from} -> {lang_to}')
            df_from = pd.read_csv(f'csv/langlinks/{lang_from}/to_{lang_to}.csv', sep='\t', header=None, index_col=0,
                                  na_filter=False)
            df = df_from.join(pd.read_csv(f'csv/page/{lang_from}.csv',
                                          sep='\t',
                                          header=None,
                                          na_filter=False,
                                          index_col=0, ),
                              rsuffix=lang_from, lsuffix=lang_to)
            df['1' + lang_to] = df['1' + lang_to].apply(lambda x: x.replace(' ', '_'))
            df_other = pd.read_csv(f'csv/page/{lang_to}.csv',
                                   sep='\t',
                                   header=None,
                                   na_filter=False,
                                   index_col=1)
            df = df.join(df_other, on='1' + lang_to)
            df.columns = [f'title_{lang_to}', f'title_{lang_from}', f'id_{lang_to}']
            df = df.dropna()
            df_other = pd.read_csv(f'csv/langlinks/{lang_to}/to_{lang_from}.csv', sep='\t', header=None, index_col=0,
                                   na_filter=False)
            df = df.join(df_other, on=f'id_{lang_to}')
            df_no_nans = df.dropna()
            broken_links = df[df.isna().any(axis=1)]
            subset = broken_links[f'title_{lang_from}'].isin(df_no_nans[f'title_{lang_from}'])
            dead_links = broken_links.loc[~subset].drop_duplicates(f'title_{lang_from}')
            duplicate_broken_links = broken_links.loc[subset]
            print('Broken backlinks:')
            pprint(dead_links[f'title_{lang_from}'].values)
            print(f'Number of broken backlinks {lang_from} -> {lang_to} -> {lang_from}: {dead_links.shape[0]}')
            print(f'Number of broken backlinks from duplicate sites: {duplicate_broken_links.shape[0]}')


def compute_stats():
    stats = pd.DataFrame(columns=MAIN_LANGS)
    for lang in MAIN_LANGS:
        df = pd.read_csv(f'csv/page/{lang}.csv',
                         sep='\t',
                         header=None,
                         na_filter=False,
                         index_col=0)
        mode = df[1].mode()
        stats.at['pages_total', lang] = len(df)
        stats.at['duplicate_pages', lang] = len(df) - len(df.drop_duplicates())
        stats.at['most_duplicated_page', lang] = list(mode.values)
        stats.at['most_page_duplicates', lang] = df[df[1] == mode.values[0]].shape[0]

    lang_stats = pd.DataFrame(columns=MAIN_LANGS, dtype='int')
    for lang_from in MAIN_LANGS:
        for lang_to in available_langs():
            if lang_to == lang_from:
                continue
            try:
                df = pd.read_csv(f'csv/langlinks/{lang_from}/to_{lang_to}.csv', sep='\t', header=None, index_col=0,
                                 na_filter=False)
                lang_stats.at[lang_to, lang_from] = int(len(df))
            except FileNotFoundError:
                lang_stats.at[lang_to, lang_from] = None

    stats = stats.append(lang_stats.describe().loc[['count', 'mean', 'max'], :])
    stats.loc['most_translated_language', :] = lang_stats.idxmax(skipna=True)
    return stats


def load_index(name):
    return index.open_dir(INDEX_DIR, name)


def term_frequency():
    for lang in MAIN_LANGS:
        idx = load_index(index_name(lang))
        with idx.reader() as reader:
            yield lang, reader.most_frequent_terms('title',
                                                   number=10), None  # reader.most_distinctive_terms('title', 10)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Get statistics')
    group = arg_parser.add_argument_group(title='Outputs', description='Specify desired outputs')
    group.add_argument('-b', '--backlinks', action='store_true', help='Check backlinks')
    group.add_argument('-s', '--stats', action='store_true', help='Show statistics')
    group.add_argument('-t', '--term_frequency', action='store_true', help='Show statistics')

    args = arg_parser.parse_args()

    if not args.backlinks and not args.stats and not args.term_frequency:
        print('No output selected.')
        arg_parser.print_help()

    if args.backlinks:
        check_backlinks()

    if args.stats:
        pd.set_option('display.max_colwidth', 20)
        print(compute_stats())

    if args.term_frequency:
        for lang, tf, dist in term_frequency():
            print(f'10 Most frequent terms {lang}wiki pages')
            df_tf = pd.DataFrame(data=tf, columns=['Collection frequency', 'Term'])
            # df_dist = pd.DataFrame(data=dist, columns=['TF*IDF', 'Term'])
            print(df_tf)
            # print(df_dist)
