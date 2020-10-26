Dokumentácia [toťka.](http://dokuwiki.ui.sav.sk/doku.php?id=user:matuspilnan:start)

# Spustenie
Na spustenie je potrebné mať nainštalovaný Python 3.8
1. Naklonovať/stiahnuť tento repozitár
2. Stiahnuť a rozbaliť SQL dumpy do priečinka `<repozitar>/wikipedia_dumps`. (page: [cs](https://dumps.wikimedia.org/cswiki/latest/cswiki-latest-page.sql.gz), [fi](https://dumps.wikimedia.org/fiwiki/latest/fiwiki-latest-page.sql.gz), [sk](https://dumps.wikimedia.org/skwiki/latest/skwiki-latest-page.sql.gz), langlinks: [cs](https://dumps.wikimedia.org/cswiki/latest/cswiki-latest-langlinks.sql.gz), [fi](https://dumps.wikimedia.org/fiwiki/latest/fiwiki-latest-langlinks.sql.gz), [sk](https://dumps.wikimedia.org/skwiki/latest/skwiki-latest-langlinks.sql.gz))
3. Nainštalovať závislosti:  `pip install -r requirements.txt` v koreňovom priečinku repozitára.
4. Spustenie jednotlivých skriptov. Každý skript má prepínač `-h`, ktorý vypíše pomoc a použitie daného skriptu.
    1. Parser - `python parser.py` - pre správne fungovanie ostatných skriptov treba tento spustiť aspoň raz
    2. Vyhľadávač - `python searcher.py`
    3. Štatistiky a overenie backlinks - `python stats.py`
