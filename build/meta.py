"""Join the archive's own README tables with the build results into site data.

Every fact on the generated page (title, author, licence, upstream link, the
one-line note) comes from the source archive's README, not from anywhere else,
so nothing on the page is invented.
"""
import os, re, json

SRC_ROOT = r"C:\github\gamebuino_classic_source_codes"
BUILD = r"C:\gbbuild"
SITE = r"C:\github\gamebuino_classic_games"

ROW = re.compile(r'^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$')
LINK = re.compile(r'\[((?:games|tools)/[^\]]+)\]\(([^)]+)\)\s*(?:\((.*)\))?\s*$')

def parse_readme():
    """folder path -> {title, author, license, url, note}"""
    out = {}
    for line in open(os.path.join(SRC_ROOT, 'README.md'), encoding='utf-8'):
        m = ROW.match(line.rstrip('\n'))
        if not m:
            continue
        title, author, lic, source = m.groups()
        if title in ('Game', 'Tool') or set(title) <= set('-: '):
            continue
        lm = LINK.search(source)
        if not lm:
            continue
        folder, url, note = lm.group(1), lm.group(2), (lm.group(3) or '')

        # The parenthetical records how the entry was recovered and, for the
        # submodule rows, usually what it actually is. Keep only that second
        # part: the "Manual download" rows say where the zip came from, which
        # is provenance rather than a description.
        note = re.sub(r'\s+', ' ', note).strip()
        desc = ''
        m2 = re.match(r'^Submodule[^-]*-\s*(.*)$', note)
        if m2:
            desc = m2.group(1).strip()
        desc = re.sub(r'`([^`]*)`', r'\1', desc)

        # drop the archive's own discovery/provenance asides
        PROV = re.compile(r'(found via|not on the wiki|wiki link|sweep|recovered|'
                          r'mirror|independently found|confirmed by direct diff|'
                          r"wiki's own)", re.I)
        clauses = [c.strip() for c in re.split(r'\s*;\s*', desc) if c.strip()]
        clauses = [c for c in clauses if not PROV.search(c)]
        desc = '; '.join(clauses)
        desc = desc[0].upper() + desc[1:] if desc else ''

        out[folder.replace('/', '\\')] = {
            'title': title.strip(),
            'author': author.strip(),
            'license': re.sub(r'\*\*|`', '', lic).strip(),
            'url': url if url.startswith('http') else None,
            'desc': desc,
        }
    return out

def main():
    readme = parse_readme()
    targets = json.load(open(os.path.join(BUILD, 'targets.json')))
    results = {}
    for f in os.listdir(os.path.join(BUILD, 'results')):
        r = json.load(open(os.path.join(BUILD, 'results', f)))
        results[r['slug']] = r

    shots = set()
    sdir = os.path.join(SITE, 'screenshots')
    if os.path.isdir(sdir):
        shots = {os.path.splitext(f)[0] for f in os.listdir(sdir) if f.endswith('.png')}

    entries, missing_meta = [], []
    for t in targets:
        r = results.get(t['slug'])
        if not r or not r['ok']:
            continue
        # the README keys most rows by game folder, but a few by the exact
        # sketch path inside it (Pong Solo lives in the official library)
        key = t['top'] + '\\' + t['entry']
        m = readme.get(t['sketch_rel']) or readme.get(key)
        if not m:
            missing_meta.append(key)
            m = {'title': t['entry'], 'author': '', 'license': '', 'url': None, 'desc': ''}

        title = m['title']
        # a folder that yielded two separate games needs them told apart
        if t['slug'] != t['entry']:
            title += ' \u2014 ' + re.sub(r'\d+$', '', os.path.splitext(t['main'])[0])

        flash = None
        if r.get('size'):
            mm = re.search(r'(\d+) bytes \((\d+)%\)', r['size'])
            if mm:
                flash = {'bytes': int(mm.group(1)), 'pct': int(mm.group(2))}

        entries.append({
            'slug': t['slug'],
            'top': t['top'],
            'title': title,
            'author': m['author'],
            'license': m['license'],
            'url': m['url'],
            'desc': m['desc'],
            'hex': t['top'] + '/' + t['slug'] + '.hex',
            'shot': ('screenshots/' + t['slug'] + '.png') if t['slug'] in shots else None,
            'prebuilt': r.get('source') == 'prebuilt',
            'flash': flash,
            'archive': 'https://github.com/joyrider3774/gamebuino_classic_source_codes/tree/main/'
                       + t['top'] + '/' + t['entry'],
        })

    entries.sort(key=lambda e: e['title'].lower())
    json.dump(entries, open(os.path.join(BUILD, 'site.json'), 'w'), indent=1)

    print('entries:', len(entries),
          '| games:', sum(1 for e in entries if e['top'] == 'games'),
          '| tools:', sum(1 for e in entries if e['top'] == 'tools'))
    print('without a screenshot:', [e['slug'] for e in entries if not e['shot']])
    print('without README metadata:', missing_meta)
    print('without a description:', sum(1 for e in entries if not e['desc']))


if __name__ == '__main__':
    main()
