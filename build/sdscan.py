"""Find every built entry whose code actually touches the SD card.

Scans the exact staged sources that were compiled, looking both for the SD
libraries a game can use and for the filenames it opens.
"""
import os, re, json

BUILD = r"C:\gbbuild"
STAGE = os.path.join(BUILD, "stage")
SRC_ROOT = r"C:\github\gamebuino_classic_source_codes"
EXT = ('.ino', '.pde', '.h', '.hpp', '.c', '.cpp')

# APIs that mean "this sketch reads or writes the SD card itself"
API = re.compile(
    r'\b(SdFat|SdFile|Sd2Card|SdVolume|PFFS|pf_open|pf_read|pf_lseek|pf_mount|'
    r'petit_fatfs|GB_Fat|GB_File|diskio|disk_readp|SD\.begin|SD\.open|'
    r'gb\.getDefaultName|readFile|openFile|loadFile)\b')

# 8.3 filenames appearing as string literals -- what it would open
FILENAME = re.compile(r'"([A-Za-z0-9_~\-]{1,8}\.[A-Za-z0-9]{1,3})"')
# the Gamebuino loader reads these itself; not game data
IGNORE_NAME = re.compile(r'\.(h|c|cpp|ino|inf|hex|png|txt|md)$', re.I)


def scan_dir(d):
    apis, names = set(), set()
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = [x for x in dirnames if x not in ('.git', 'libraries', 'lib')]
        for fn in filenames:
            if not fn.lower().endswith(EXT):
                continue
            try:
                t = open(os.path.join(dirpath, fn), encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            t = re.sub(r'//[^\n]*', '', t)                 # drop line comments
            t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)    # and block comments
            apis.update(m.group(0) for m in API.finditer(t))
            for m in FILENAME.finditer(t):
                if not IGNORE_NAME.search(m.group(1)):
                    names.add(m.group(1))
    return apis, names


def main():
    targets = {t['slug']: t for t in json.load(open(os.path.join(BUILD, 'targets.json')))}
    hits = []
    for slug, t in sorted(targets.items()):
        # Scan only the sketch directory that was actually compiled. Scanning
        # the whole repo produces false positives: the Gamebuino library folder
        # also carries the SD-based Loader example, and CopterStrike keeps a
        # separate mini-loader sketch next to the game.
        if not t.get('sketch_rel'):
            continue
        d = os.path.join(STAGE, slug, t['entry'])
        rel = os.path.relpath(os.path.join(SRC_ROOT, t['sketch_rel']),
                              os.path.join(SRC_ROOT, t['top'], t['entry']))
        if rel != '.':
            d = os.path.join(d, rel)
        if not os.path.isdir(d):
            # the fix-ups may have renamed the sketch dir to its main .ino
            d = os.path.join(os.path.dirname(d), os.path.splitext(t['main'])[0])
        if not os.path.isdir(d):
            continue
        apis, names = scan_dir(d)
        if not apis and not names:
            continue

        # what data-looking files does the source folder actually ship?
        shipped = []
        gdir = os.path.join(SRC_ROOT, t['top'], t['entry'])
        for dp, dn, fs in os.walk(gdir):
            dn[:] = [x for x in dn if x != '.git']
            for f in fs:
                if f.lower().endswith(('.dat', '.raw', '.bin', '.img', '.sav', '.mid')):
                    shipped.append(os.path.relpath(os.path.join(dp, f), gdir))
        hits.append({'slug': slug, 'apis': sorted(apis),
                     'filenames': sorted(names), 'shipped': sorted(shipped)})

    for h in hits:
        print('%-32s api=%-46s opens=%-28s ships=%s' % (
            h['slug'], ','.join(h['apis'])[:45] or '-',
            ','.join(h['filenames'])[:27] or '-',
            ','.join(h['shipped']) or '-'))
    print('\n%d of %d entries touch the SD card or name a data file'
          % (len(hits), len(targets)))
    json.dump(hits, open(os.path.join(BUILD, 'sdscan.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
