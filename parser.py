import glob
from pprint import pprint
import re
from parse import *
from parse import compile, findall
import pandas as pd


def get_filenames(path='', extension='.mp3'):
    if path[-1] == '/' or path[-1] == '\\':
        path = path + '*' + extension
    elif len(path) > 0:
        path = path + '/*' + extension

    filenames = glob.glob(pathname=path)
    result = [filename for filename in filenames]
    result.sort()
    return result


path = 'wikipedia_dumps\\'

filename_parser = compile(path+'{lang}wiki-latest-{tablename}.sql')
page_parser = compile("({page_id:d},{namespace:d},'{page_title}',{rest})")
langlink_parser = compile("({page_id:d},'{target_lang}','{target_title}')")

files = get_filenames(path, '.sql')
# files = ['wikipedia_dumps\\skwiki-latest-page.sql']
pages = dict()
langlinks = dict()

for file in files:
    print(f'parsing {file}...')
    filename_result = filename_parser.search(file)
    lang = filename_result['lang']
    if filename_result['tablename'] == 'page':
        parser = page_parser
        collection = pages
    else:
        parser = langlink_parser
        collection = langlinks
    with open(file, 'r', encoding='utf8', errors='ignore') as f:
        for line in f:
            if line.startswith('INSERT INTO'):
                start = line.find('(')
                line = line[start:]
                result = parser.findall(line)

                if filename_result['tablename'] == 'page':
                    new_entries = pd.DataFrame([(r['page_id'], r['page_title']) for r in result],
                                 columns=['id', 'title'])
                else:
                    new_entries = pd.DataFrame([(r['page_id'], r['target_lang'], r['target_title']) for r in result],
                                               columns=['id', 'target_lang', 'target_title'])
                try:
                    if collection[lang] is not None:
                        collection[lang].append(new_entries)
                    else:
                        collection[lang] = new_entries
                except KeyError:
                    collection[lang] = new_entries
        collection[lang].to_csv(f'csv/{filename_result["tablename"]}/{lang}.csv')
    pass
