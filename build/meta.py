"""Join the archive's own README tables with the build results into site data.

Every fact on the generated page (title, author, licence, upstream link, the
one-line note) comes from the source archive's README, not from anywhere else,
so nothing on the page is invented.
"""
import os, re, json

SRC_ROOT = r"C:\github\gamebuino_classic_source_codes"
BUILD = r"C:\gbbuild"
SITE = os.environ.get("GB_SITE", r"C:\github\gamebuino_classic_games_compiled")

ROW = re.compile(r'^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$')
LINK = re.compile(r'\[((?:games|tools)(?:_precompiled)?/[^\]]+)\]\(([^)]+)\)\s*(?:\((.*)\))?\s*$')


# Entries whose build depends on a library that does not survive anywhere and
# was written from scratch here. Everything else on the page is either a
# faithful rebuild or the author's own binary, so the difference is worth
# saying on the card rather than burying in a README.
RECONSTRUCTED = {
    'makerbuino-frequency-generator':
        "Built against a reconstructed gamebuino_main_alt.h. The author never "
        "published that header; the version here is a shim onto the stock "
        "Gamebuino library, which supplies every symbol this sketch uses, so "
        "its behaviour should be unchanged.",
    'makerbuino-sd-explorer':
        "Built against two things written from scratch here: "
        "gamebuino_main_alt.h, and the author's unbuffered DISPLAYDIRECT "
        "display mode, which this sketch needs to fit in RAM. Neither survives "
        "anywhere. The drawing code is therefore not the author's.",
    'makerbuino-midi':
        "Built against a MidiSdFatBase.h written from scratch here - the glue "
        "between the author's Midi2 library and SdFat, which he never "
        "published. The MIDI file parsing is therefore not the author's.",
}


def submodule_paths():
    """Folders the archive stores as a submodule rather than as real files.

    A submodule is only a pointer: browsing that folder on GitHub shows a commit
    reference, not the game's source. Linking to it as "archived source" would
    be a dead end, so those entries link to the upstream repository instead.
    """
    out = set()
    gm = os.path.join(SRC_ROOT, '.gitmodules')
    if not os.path.isfile(gm):
        return out
    for line in open(gm, encoding='utf-8', errors='replace'):
        m = re.match(r'\s*path\s*=\s*(\S+)', line)
        if m:
            out.add(m.group(1).replace('\\', '/').strip('/'))
    return out

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
    submodules = submodule_paths()
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

        folder = t['top'] + '/' + t['entry']
        is_submodule = folder in submodules
        # the archive files binary-only recoveries in their own category; the
        # site keeps two folders and marks the distinction on the card instead
        site_dir = t.get('site_dir') or t['top']
        entries.append({
            'slug': t['slug'],
            'top': site_dir,
            'title': title,
            'author': m['author'],
            'license': m['license'],
            'url': m['url'],
            'desc': m['desc'],
            'hex': site_dir + '/' + t['slug'] + '.hex',
            'shot': ('screenshots/' + t['slug'] + '.png') if t['slug'] in shots else None,
            'prebuilt': r.get('source') == 'prebuilt',
            # no source for this one exists anywhere; the archive recovered a
            # compiled binary only
            'precompiled': bool(t.get('precompiled')),
            'reconstructed': RECONSTRUCTED.get(t['slug']),
            'flash': flash,
            'submodule': is_submodule,
            # only entries the archive really holds get an archive link
            'archive': None if is_submodule else
                       'https://github.com/joyrider3774/gamebuino_classic_source_codes/tree/main/'
                       + folder,
        })

    entries.sort(key=lambda e: e['title'].lower())
    json.dump(entries, open(os.path.join(BUILD, 'site.json'), 'w'), indent=1)

    print('entries:', len(entries),
          '| games:', sum(1 for e in entries if e['top'] == 'games'),
          '| tools:', sum(1 for e in entries if e['top'] == 'tools'))
    print('without a screenshot:', [e['slug'] for e in entries if not e['shot']])
    print('without README metadata:', missing_meta)
    print('without a description:', sum(1 for e in entries if not e['desc']))
    subs = [e for e in entries if e['submodule']]
    print('submodules (upstream link only):', len(subs),
          '| really archived here:', len(entries) - len(subs))
    print('built against a reconstructed dependency:',
          [e['slug'] for e in entries if e.get('reconstructed')])
    print('binary-only recoveries:', sum(1 for e in entries if e['precompiled']),
          '| built from source:', sum(1 for e in entries
                                      if not e['precompiled'] and not e['prebuilt']))
    orphans = [e['slug'] for e in entries if not e['archive'] and not e['url']]
    if orphans:
        print('WARNING - no source link at all:', orphans)


if __name__ == '__main__':
    main()
