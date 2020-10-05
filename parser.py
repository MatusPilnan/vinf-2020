import glob
import os

from parse import compile


def close_files(d: dict):
    for k, v in d.items():
        if isinstance(v, dict):
            close_files(v)
        else:
            try:
                print(f'Closing file {f.name}')
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


path = 'wikipedia_dumps\\'

filename_parser = compile(path + '{lang}wiki-latest-{tablename}.sql')
page_parser = compile("({page_id:d},{namespace:d},'{page_title}',{rest})")
langlink_parser = compile("({page_id:d},'{target_lang}','{target_title}')")

files = get_filenames(path, '.sql')
# files = ['wikipedia_dumps\\skwiki-latest-page.sql']
page_files = dict()
langlink_files = dict()

for file in files:
    print(f'parsing {file}...')
    filename_result = filename_parser.search(file)
    lang = filename_result['lang']
    tablename = filename_result['tablename']
    if tablename == 'page':
        parser = page_parser
    else:
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
                        target_file.write(f'{r["page_id"]},{r["page_title"]}\n')
                    except (KeyError, NameError):
                        try:
                            target_file = langlink_files[lang][r['target_lang']]
                        except KeyError:
                            os.makedirs(f'csv/{tablename}/{lang}', exist_ok=True)
                            target_file = open(f'csv/{tablename}/{lang}/to_{r["target_lang"]}.csv', 'w',
                                               encoding='utf8')
                            try:
                                langlink_files[lang][r['target_lang']] = target_file
                            except KeyError:
                                langlink_files[lang] = dict()
                                langlink_files[lang][r['target_lang']] = target_file
                        target_file.write(f'{r["page_id"]},{r["target_title"]}\n')
    close_files(page_files)
    close_files(langlink_files)
