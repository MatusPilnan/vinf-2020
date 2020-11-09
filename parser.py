import argparse
import glob
import json
import os

from parse import compile
from whoosh.fields import *
from whoosh.index import create_in

from common import INDEX_DIR, page_schema, MAIN_LANGS, index_name

args = None
start_time = None
if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Parse wikipedia SQL dumps')
    arg_parser.add_argument('-p', '--pages_only', help='Only parse pages', action='store_true')
    arg_parser.add_argument('-l', '--langlinks_only', help='Only parse langlinks', action='store_true')
    arg_parser.add_argument('-t', '--time', help='Whether to time the execution', action='store_true')

    args = arg_parser.parse_args()


def close_files(d: dict):
    for k, v in d.items():
        if isinstance(v, dict):
            close_files(v)
        else:
            try:
                print(f'Closing file {v.name}')
                v.close()
            except:
                print(f'Cant close file: {v}')


def get_filenames(path='', extension='.mp3'):
    if path[-1] == '/' or path[-1] == '\\':
        path = path + '*' + extension
    elif len(path) > 0:
        path = path + '/*' + extension

    filenames = glob.glob(pathname=path)
    result = [filename for filename in filenames]
    result.sort()
    return result


if args.time:
    start_time = datetime.datetime.now()
path = 'wikipedia_dumps\\'

filename_parser = compile(path + '{lang}wiki-latest-{tablename}.sql')
page_parser = compile("({page_id:d},{namespace:d},'{page_title}',{rest})")
langlink_parser = compile("({page_id:d},{target_lang},{target_title})")

files = get_filenames(path, '.sql')
os.makedirs(INDEX_DIR, exist_ok=True)

idx_page = dict()
page_writers = dict()
if not args.langlinks_only:
    if os.path.exists(INDEX_DIR):
        input('Index directory already exists. If you want to continue and discard existing index, press Enter.')

    for lang in MAIN_LANGS:
        idx_page[lang] = create_in(INDEX_DIR, page_schema, indexname=index_name(lang))
        page_writers[lang] = idx_page[lang].writer(limitmb=1024)
page_files = dict()
langlink_files = dict()
languages = set()

for file in files:
    print(f'parsing {file}...')
    filename_result = filename_parser.search(file)
    lang = filename_result['lang']
    tablename = filename_result['tablename']
    if tablename == 'page':
        if args.langlinks_only:
            continue
        parser = page_parser
    else:
        if args.pages_only:
            continue
        parser = langlink_parser
    with open(file, 'r', encoding='utf8', errors='ignore') as f:
        for line in f:
            if line.startswith('INSERT INTO'):
                start = line.find('(')
                line = line[start:]
                result = parser.findall(line)
                if tablename == 'page':
                    try:
                        target_file = page_files[lang]
                    except KeyError:
                        os.makedirs(f'csv/{tablename}', exist_ok=True)
                        target_file = open(f'csv/{tablename}/{lang}.csv', 'w', encoding='utf8')
                        page_files[lang] = target_file

                for r in result:
                    try:
                        target_file.write(f'{r["page_id"]}\t{r["page_title"]}\n')
                        page_writers[lang].add_document(id=r['page_id'], title=r['page_title'].replace('_', ' '))
                    except (KeyError, NameError):
                        target_lang = r['target_lang'].strip("'")
                        try:
                            target_file = langlink_files[lang][target_lang]
                            languages.add(target_lang)
                        except KeyError:
                            os.makedirs(f'csv/{tablename}/{lang}', exist_ok=True)
                            target_file = open(f'csv/{tablename}/{lang}/to_{target_lang}.csv', 'w',
                                               encoding='utf8')
                            try:
                                langlink_files[lang][target_lang] = target_file
                            except KeyError:
                                langlink_files[lang] = dict()
                                langlink_files[lang][target_lang] = target_file
                        target_title = r['target_title'].strip("'")
                        target_file.write(f'{r["page_id"]}\t{target_title}\n')
    close_files(page_files)
    close_files(langlink_files)
for key, page_writer in page_writers.items():
    print(f'Comitting writer {key}...')
    page_writer.commit()
    print(f'Writer {key} committed.')

with open('info.json') as info_file:
    try:
        info = json.load(info_file)
    except json.decoder.JSONDecodeError:
        info = {}

with open('info.json', 'w') as info_file:
    info['lastParse'] = datetime.datetime.now().timestamp()
    if not args.pages_only:
        info['allLangs'] = list(languages)
    json.dump(info, info_file, indent=2)

if start_time:
    print(f'Parsing took {datetime.datetime.now() - start_time}')
