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
    # Neither of these is a program: both are ready-made SD cards bundling
    # dozens of prebuilt .HEX games. The archive's own games_precompiled/
    # category is where the individual titles mined out of them now live.
    'tools_precompiled/Gamebuino-Classic-Games-Compilation',
    'tools_precompiled/Gamebuino-Classic_Games',
    # custom "Educational Use License": non-commercial only, and it restricts
    # redistribution/mirroring, so its build is not published here
    'tools/gamebuinoEducation',
}

# the archive files binary-only finds separately; those keep the distinction
PRECOMPILED_TOPS = ('games_precompiled', 'tools_precompiled')

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
    # Our rebuild of discovery never leaves the library's title screen --
    # pressing A does nothing and it sits there indefinitely, while the
    # author's own binary goes straight into the game. Ship the author's.
    'discovery': 'games/discovery/Discovery.ino.standard.hex',
    # A rebuild of sokobuino against the modern toolchain comes up with
    # corrupted game state -- current_gui_state lands on 4, which matches no
    # branch in its loop(), so it draws nothing. The author's own .hex runs
    # correctly, so that is what ships.
    'sokobuino': r'games\sokobuino\sokobuino.hex',
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

# An entry with no sketch but exactly one .hex is a binary-only recovery: ship
# the binary. This covers the whole games_precompiled/ + tools_precompiled/
# categories as well as the odd source-bearing folder that only kept its build.
for o in out:
    if o.get('use_prebuilt') or o.get('main'):
        continue
    hexes = [h for h in o['prebuilt_hex'] if not h.lower().endswith('.with_bootloader.hex')]
    if len(hexes) == 1:
        o['use_prebuilt'] = hexes[0]

# the site keeps two folders; the precompiled categories fold into them and are
# told apart by their own flag rather than by a directory
for o in out:
    o['precompiled'] = o['top'] in PRECOMPILED_TOPS
    o['site_dir'] = 'tools' if o['top'].startswith('tools') else 'games'

json.dump(out, open(r'C:\gbbuild\targets.json', 'w'), indent=1)
print('targets:', len(out),
      '| games:', sum(1 for o in out if o['site_dir'] == 'games'),
      '| tools:', sum(1 for o in out if o['site_dir'] == 'tools'))
print('  built from source:', sum(1 for o in out if o.get('main')),
      '| shipped as a binary:', sum(1 for o in out if o.get('use_prebuilt')),
      '| of those, binary-only finds:', sum(1 for o in out if o['precompiled']))
orphan = [o['slug'] for o in out if not o.get('main') and not o.get('use_prebuilt')]
if orphan:
    print('  NO SOURCE AND NO SINGLE HEX:', orphan)
for o in out:
    if o['slug'] != o['entry']:
        print('  split:', o['slug'], '<-', o['sketch_rel'])
