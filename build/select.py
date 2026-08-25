import os, json, re

D = json.load(open(r'C:\gbbuild\discovery.json'))

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def slashed(p):
    return '/' + p.replace('\\', '/').lower() + '/'

# path segments that mark a non-primary/archived copy of a sketch
DEAD = ('/archive/', '/old/', '/other/', '/backup/', '/test/', '/tests/')

# Gamebuino-Classic-Games-Compilation is not a program at all -- it is a
# ready-made SD card holding 50 prebuilt .HEX games that are each already
# covered by their own entry. Kept out of the playable list on purpose.
SKIP_ENTRY = {
    'tools/Gamebuino-Classic-Games-Compilation',
    # custom "Educational Use License": non-commercial only, and it restricts
    # redistribution/mirroring, so its build is not published here
    'tools/gamebuinoEducation',
}

# for multi-sketch entries, keep only sketch dirs ending with one of these
FORCE = {
    'games/Gamebuino-Classic': ['2.Intermediate/Pong'],
    'games/StijnCaerts-Gamebuino': ['StijnCaerts-Gamebuino/Pong', 'StijnCaerts-Gamebuino/Snake'],
}

# targets whose sketch file does not exist in the archive as-is and is
# materialised by that slug's fix-up script
MANUAL = [
    # a plain Arduino sketch that ships as hello.cpp for a CMake build
    {'top': 'tools', 'entry': 'HelloGamebuino', 'slug': 'HelloGamebuino',
     'sketch_rel': r'tools\HelloGamebuino', 'main': 'HelloGamebuino.ino'},
]

# entries shipped only as a prebuilt .hex (path relative to the archive root)
PREBUILT = {
    'DarkTower': r'games\DarkTower\DARKTOWR.HEX',
    'DeathMaze': r'games\DeathMaze\DEATHMAZ.HEX',
    'Gamebuino-SuperSpaceShooter':
        r'games\Gamebuino-SuperSpaceShooter\dist\Debug\Arduino-Windows\superspaceshooter.hex',
    # B-Rally's normal build needs a SD-card FAT driver; the author shipped a
    # Simbuino-specific build alongside it, which is the one that runs here
    'B-Rally': r'games\B-Rally\bin\B-Rally_SimbuinoVersion.hex',
}

out = []
for e in D:
    key = e['top'] + '/' + e['name']
    if key in SKIP_ENTRY:
        continue
    sks = [s for s in e['sketches'] if s['main']]
    if key in FORCE:
        want = FORCE[key]
        sks = [s for s in sks if any(slashed(s['rel']).endswith(w.lower() + '/') for w in want)]
    else:
        live = [s for s in sks if not any(d in slashed(s['rel']) for d in DEAD)]
        if live:
            sks = live
        if len(sks) > 1:
            n = norm(e['name'])
            best = [s for s in sks
                    if norm(os.path.basename(s['dir'])) == n
                    or norm(os.path.splitext(s['main'])[0]) == n]
            if best:
                sks = best[:1]
            else:
                sks = sorted(sks, key=lambda s: (s['rel'].count('\\'), len(s['rel'])))[:1]
    for s in sks:
        slug = e['name'] if len(sks) == 1 else e['name'] + '-' + os.path.splitext(s['main'])[0]
        out.append({
            'top': e['top'], 'entry': e['name'], 'slug': slug,
            'sketch_rel': s['rel'], 'main': s['main'],
            'prebuilt_hex': e['prebuilt_hex'],
        })

for m in MANUAL:
    if not any(o['slug'] == m['slug'] for o in out):
        out.append(dict(m, prebuilt_hex=[]))

# entries with no compilable sketch at all (may still ship a prebuilt .hex)
for e in D:
    key = e['top'] + '/' + e['name']
    if key in SKIP_ENTRY:
        continue
    if not any(o['entry'] == e['name'] and o['top'] == e['top'] for o in out):
        out.append({'top': e['top'], 'entry': e['name'], 'slug': e['name'],
                    'sketch_rel': None, 'main': None, 'prebuilt_hex': e['prebuilt_hex']})

for o in out:
    if o['slug'] in PREBUILT:
        o['use_prebuilt'] = PREBUILT[o['slug']]

json.dump(out, open(r'C:\gbbuild\targets.json', 'w'), indent=1)
print('targets:', len(out),
      '| games:', sum(1 for o in out if o['top'] == 'games'),
      '| tools:', sum(1 for o in out if o['top'] == 'tools'))
print('no sketch:', [o['slug'] for o in out if not o['main']])
for o in out:
    if o['slug'] != o['entry']:
        print('  split:', o['slug'], '<-', o['sketch_rel'])
