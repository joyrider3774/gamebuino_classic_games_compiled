import os, re, json, sys

ROOT = r"C:\github\gamebuino_classic_source_codes"
SKIP_DIR = {'.git', '.github', 'images', 'img', 'doc', 'docs', 'dist', 'build'}

def sketch_dirs(base):
    """Return {dir: [ino files]} for every dir containing .ino/.pde files."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        inos = sorted(f for f in filenames if f.lower().endswith(('.ino', '.pde')))
        if inos:
            out[dirpath] = inos
    return out

def has_setup_loop(path):
    try:
        t = open(path, 'r', encoding='utf-8', errors='replace').read()
    except OSError:
        return False
    return bool(re.search(r'\bvoid\s+setup\s*\(', t)) and bool(re.search(r'\bvoid\s+loop\s*\(', t))

results = []
for top in ('games', 'tools', 'games_precompiled', 'tools_precompiled'):
    base = os.path.join(ROOT, top)
    if not os.path.isdir(base):
        continue
    for entry in sorted(os.listdir(base)):
        gdir = os.path.join(base, entry)
        if not os.path.isdir(gdir):
            continue
        found = sketch_dirs(gdir)
        sketches = []
        for d, inos in sorted(found.items()):
            dname = os.path.basename(d)
            main = None
            # 1. ino matching its folder name
            for i in inos:
                if os.path.splitext(i)[0].lower() == dname.lower():
                    main = i
                    break
            # 2. sole ino
            if main is None and len(inos) == 1:
                main = inos[0]
            # 3. the one with setup()+loop()
            if main is None:
                cands = [i for i in inos if has_setup_loop(os.path.join(d, i))]
                if len(cands) == 1:
                    main = cands[0]
                elif cands:
                    main = sorted(cands, key=lambda x: (len(x), x))[0]
            sketches.append({
                'dir': d, 'inos': inos, 'main': main,
                'rel': os.path.relpath(d, ROOT),
            })
        hexes = []
        for dirpath, dirnames, filenames in os.walk(gdir):
            dirnames[:] = [d for d in dirnames if d != '.git']
            for f in filenames:
                if f.lower().endswith('.hex'):
                    hexes.append(os.path.relpath(os.path.join(dirpath, f), ROOT))
        results.append({'top': top, 'name': entry, 'sketches': sketches, 'prebuilt_hex': hexes})

json.dump(results, open(r'C:\gbbuild\discovery.json', 'w'), indent=1)

nsk = sum(len(r['sketches']) for r in results)
print("entries:", len(results), " sketch dirs:", nsk)
for r in results:
    if len(r['sketches']) != 1:
        print(f"[{len(r['sketches'])}] {r['top']}/{r['name']}: " +
              ", ".join(s['rel'] + '=>' + str(s['main']) for s in r['sketches']))
