"""Batch-compile every discovered Gamebuino Classic sketch to an Intel .hex.

Each target is staged into its own folder (the whole original game folder is
copied so that any ../ relative include still resolves), the sketch directory
is renamed to match its main .ino when they differ -- which is what the
Arduino builder requires -- and then arduino-builder is run against it.
"""
import os, re, sys, json, shutil, subprocess, threading, queue, time

SRC_ROOT = r"C:\github\gamebuino_classic_source_codes"
ARDUINO = r"C:\arduino"
BUILD = r"C:\gbbuild"
STAGE = os.path.join(BUILD, "stage")
HEXOUT = os.path.join(BUILD, "hex")
LOGS = os.path.join(BUILD, "logs")
RESULTS = os.path.join(BUILD, "results")
BPROOT = os.path.join(BUILD, "bp")
FQBN = "arduino:avr:uno"

EXTRA_LIBS = os.path.join(BUILD, "libs")   # locally vendored fix-up libraries

GB_LIB = os.path.join(ARDUINO, 'portable', 'sketchbook', 'libraries', 'Gamebuino_Classic')

# Gamebuino Classic's library is configured by editing utility/settings.c, and
# the era's workflow was to copy a game's own settings.c over the library's
# before building. Two things there matter a lot:
#
#   NUM_CHANNELS  defaults to 1, and Sound::playTrack/playPattern simply
#                 `return` when asked for a channel >= NUM_CHANNELS. A game
#                 whose music plays on channel 1 or 2 compiles and runs fine
#                 but is mute, while its channel-0 effects still play.
#   ENABLE_GUI    changes whether the library's menu/volume UI is compiled in.
#
# A game shipping its own settings.c gets it used verbatim (see use_own_settings).
# For games that need more channels but ship no settings.c, the count is listed
# here instead. Regenerate with chanscan.py.
SOUND_CHANNELS = {
    'Super-Crate-Buino': 3,
    'MasterKebab': 2,
    'gamebuino-community-rpg': 2,
}


def ignore_vcs(_dir, names):
    return [n for n in names if n in ('.git', '.svn', '.hg')]


def stage(t):
    """Copy the game folder into its own staging dir; return the main .ino path."""
    dst_root = os.path.join(STAGE, t['slug'])
    if os.path.isdir(dst_root):
        shutil.rmtree(dst_root, ignore_errors=True)
    src_game = os.path.join(SRC_ROOT, t['top'], t['entry'])
    dst_game = os.path.join(dst_root, t['entry'])
    shutil.copytree(src_game, dst_game, ignore=ignore_vcs, symlinks=False)

    # locate the staged sketch dir (same relative position as in the source)
    rel_from_game = os.path.relpath(os.path.join(SRC_ROOT, t['sketch_rel']), src_game)
    sk_dir = dst_game if rel_from_game == '.' else os.path.join(dst_game, rel_from_game)

    stem = os.path.splitext(t['main'])[0]
    ext = os.path.splitext(t['main'])[1]

    # a .pde has to become a .ino for the 1.8 builder
    if ext.lower() == '.pde':
        os.rename(os.path.join(sk_dir, t['main']), os.path.join(sk_dir, stem + '.ino'))

    # Arduino requires sketchdir basename == main sketch basename
    if os.path.basename(sk_dir) != stem:
        new_dir = os.path.join(os.path.dirname(sk_dir), stem)
        if os.path.normcase(new_dir) != os.path.normcase(sk_dir):
            if os.path.exists(new_dir):
                shutil.rmtree(new_dir, ignore_errors=True)
            os.rename(sk_dir, new_dir)
        # for the many repos whose sketch sits at the top level, that rename
        # just moved the game root as well
        if os.path.normcase(sk_dir) == os.path.normcase(dst_game):
            dst_game = new_dir
        sk_dir = new_dir

    apply_fixups(t, sk_dir, dst_game)
    return os.path.join(sk_dir, stem + '.ino')


SRC_EXT = ('.ino', '.pde', '.h', '.hpp', '.c', '.cpp')


def strip_nbsp(sk_dir):
    """Remove stray non-breaking spaces / BOMs that modern avr-gcc rejects.

    Several of these sketches were pasted out of a web forum and carry U+00A0
    where a plain space belongs; the 2012-era toolchain accepted them.
    """
    for dirpath, _dirnames, filenames in os.walk(sk_dir):
        for fn in filenames:
            if not fn.lower().endswith(SRC_EXT):
                continue
            p = os.path.join(dirpath, fn)
            raw = open(p, 'rb').read()
            new = raw
            if new.startswith(b'\xef\xbb\xbf'):
                new = new[3:]
            # Decode first, then substitute. A blind byte-level replace of
            # 0xa0 would eat the trailing byte of any two-byte UTF-8 char
            # that ends in 0xa0 -- 'a-grave' is C3 A0 -- and several of these
            # sketches are French.
            try:
                text = new.decode('utf-8')
            except UnicodeDecodeError:
                text = new.decode('cp1252', errors='replace')
            new = text.replace(chr(0xa0), ' ').encode('utf-8')
            if new != raw:
                open(p, 'wb').write(new)


DEFINE = re.compile(r'^\s*#\s*define\s+(\w+)', re.M)


def private_library(game_root):
    """Copy the Gamebuino library into the staged game so it can be configured."""
    dst = os.path.join(game_root, 'libraries', 'Gamebuino_Classic')
    if not os.path.isdir(dst):
        shutil.copytree(GB_LIB, dst, ignore=ignore_vcs)
    return os.path.join(dst, 'utility', 'settings.c')


def find_own_settings(sk_dir, game_root):
    """The game's own copy of the library's settings.c, if it ships one."""
    skip = {'.git', 'libraries', 'lib'}
    for root in (sk_dir, game_root):
        for dirpath, dirnames, filenames in os.walk(root):
            # a game that vendors its library under Libraries/ must not have
            # that copy's settings.c mistaken for one of its own
            dirnames[:] = [d for d in dirnames if d.lower() not in skip]
            if 'settings.c' in filenames:
                # ...but a settings.c sitting in a vendored library's utility/
                # folder belongs to that library, not to the game
                if os.path.isfile(os.path.join(dirpath, os.pardir, 'Gamebuino.h')):
                    continue
                p = os.path.join(dirpath, 'settings.c')
                text = open(p, encoding='utf-8', errors='replace').read()
                if 'NUM_CHANNELS' in text and 'SETTINGS_C' in text:
                    return p, text
    return None, None


# settings.c divides itself into a block the author is invited to change and a
# block it says to leave alone. Only the first block is a per-game choice; the
# second holds constants that belong to a particular library release.
EDITABLE_MARKER = 'SETTINGS YOU CAN EDIT'
LEAVE_ALONE_MARKER = 'LEAVE THE FOLLOWING SETTINGS ALONE'


def vendored_library(game_root):
    """Move a library the game ships with it onto the builder's search path.

    A few of these repositories carry their own patched copy of the Gamebuino
    library next to the sketch (Gamebookuino's adds a popup(const char*)
    overload its code depends on). arduino-builder wants a directory *of*
    libraries, so the copy is relocated under <game>/libraries/, which build.py
    already passes with -libraries.
    """
    dest_root = os.path.join(game_root, 'libraries')
    found = []
    for name in sorted(os.listdir(game_root)):
        d = os.path.join(game_root, name)
        if not os.path.isdir(d) or name.lower() in ('libraries', 'lib', '.git'):
            continue
        if os.path.isfile(os.path.join(d, 'Gamebuino.h')):
            found.append((name, d))
    for name, d in found:
        os.makedirs(dest_root, exist_ok=True)
        dst = os.path.join(dest_root, name)
        if not os.path.isdir(dst):
            shutil.copytree(d, dst, ignore=ignore_vcs)
    return [n for n, _ in found]


def configure_library(t, sk_dir, game_root):
    """Apply the game's intended library configuration to a private copy."""
    own, text = find_own_settings(sk_dir, game_root)
    if own:
        stock = open(os.path.join(GB_LIB, 'utility', 'settings.c'),
                     encoding='utf-8', errors='replace').read()
        # Take only the author's game-level choices. His file predates this
        # library release, and its "leave alone" constants belong to the older
        # sound code: 101Starships ships VOLUME_GLOBAL_MAX 1, but 0.5.2 scales
        # output by `<< globalVolume) / 128` and falls back to globalVolume =
        # VOLUME_GLOBAL_MAX when no settings page is present, so carrying that
        # value over quantises every sample to zero -- dead silence.
        cut = text.find(LEAVE_ALONE_MARKER)
        if cut < 0:
            cut = len(text)
        wanted = {}
        for line in text[:cut].splitlines():
            m = DEFINE.match(line)
            if m:
                wanted[m.group(1)] = line

        out = []
        for line in stock.splitlines():
            m = DEFINE.match(line)
            out.append(wanted[m.group(1)] if m and m.group(1) in wanted else line)
        open(private_library(game_root), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
        return

    n = SOUND_CHANNELS.get(t['slug'])
    if not n:
        return
    settings = private_library(game_root)
    stock = open(settings, encoding='utf-8', errors='replace').read()
    new, count = re.subn(r'(#define\s+NUM_CHANNELS\s+)\d+',
                         lambda m: m.group(1) + str(n), stock, count=1)
    if count != 1:
        raise RuntimeError('could not set NUM_CHANNELS in ' + settings)
    open(settings, 'w', encoding='utf-8').write(new)


def progmem_const(sk_dir, names=None):
    """Make PROGMEM declarations const, as avr-gcc has required since 4.6.

    Handles the spellings these sketches use, leaves anything already const or
    `extern` alone, and keeps PROGMEM in place rather than dropping it (which
    would move the data into the 2 KB of RAM). Pass `names` to limit the change
    to particular variables.
    """
    want = set(names) if names else None

    def fix(line):
        if 'PROGMEM' not in line or re.search(r'\bextern\b', line):
            return line
        head, sep, tail = line.partition('=')
        if not sep:
            m = re.match(r'^(\s*)([\w\s\*]+?\s+(\w+)\s*\[[^\]]*\])\s*PROGMEM\b', line)
            if m and not re.search(r'\bconst\b', line):
                if want and m.group(3) not in want:
                    return line
                return line.replace(m.group(2), 'const ' + m.group(2), 1)
            return line

        # PROGMEM <type>* name[] =   ->   const <type>* const name[] PROGMEM =
        m = re.match(r'^(\s*)PROGMEM\s+(?:const\s+)?(.+?)\s*(\*+)\s*(\w+)\s*(\[[^\]]*\])\s*$', head)
        if m:
            if want and m.group(4) not in want:
                return line
            return (m.group(1) + 'const ' + m.group(2) + m.group(3) + ' const '
                    + m.group(4) + m.group(5) + ' PROGMEM =' + tail)

        # PROGMEM <type> name[] =    ->   const <type> name[] PROGMEM =
        m = re.match(r'^(\s*)PROGMEM\s+(?:const\s+)?([\w\s]+?)\s+(\w+)\s*(\[[^\]]*\])\s*$', head)
        if m:
            if want and m.group(3) not in want:
                return line
            return (m.group(1) + 'const ' + m.group(2) + ' ' + m.group(3)
                    + m.group(4) + ' PROGMEM =' + tail)

        # const <type>* name[] PROGMEM =  ->  const <type>* const name[] PROGMEM =
        # (the elements are const, but the array itself has to be too)
        m = re.match(r'^(\s*)(.*\*)\s*(\w+)\s*(\[[^\]]*\])\s*PROGMEM\s*$', head)
        if m and not re.search(r'\*\s*const\s*$', m.group(2) + ' '):
            if want and m.group(3) not in want:
                return line
            lead = m.group(2) if re.match(r'^\s*const\b', m.group(2)) else 'const ' + m.group(2).lstrip()
            return (m.group(1) + lead + ' const ' + m.group(3) + m.group(4)
                    + ' PROGMEM =' + tail)

        if re.search(r'\bconst\b', head):
            return line

        # <type> name[] PROGMEM =    ->   const <type> name[] PROGMEM =
        m = re.match(r'^(\s*)([\w\s\*]+?\s+(\w+)\s*\[[^\]]*\])\s*PROGMEM\s*$', head)
        if m:
            if want and m.group(3) not in want:
                return line
            return line.replace(m.group(2), 'const ' + m.group(2), 1)
        return line

    for dirpath, dirnames, filenames in os.walk(sk_dir):
        dirnames[:] = [d for d in dirnames if d.lower() != '.git']
        for fn in filenames:
            if not fn.lower().endswith(SRC_EXT):
                continue
            fp = os.path.join(dirpath, fn)
            with open(fp, encoding='utf-8', errors='surrogateescape') as f:
                lines = f.read().split(chr(10))
            out = [fix(l) for l in lines]
            if out != lines:
                with open(fp, 'w', encoding='utf-8', errors='surrogateescape') as f:
                    f.write(chr(10).join(out))


def apply_fixups(t, sk_dir, game_root):
    strip_nbsp(sk_dir)
    vendored = vendored_library(game_root)
    # a game that brings its own library keeps it; do not shadow it with the
    # installed one
    if not vendored:
        configure_library(t, sk_dir, game_root)
    fx = os.path.join(BUILD, 'fixups', t['slug'] + '.py')
    if os.path.isfile(fx):
        env = {'SKETCH_DIR': sk_dir, 'GAME_ROOT': game_root,
               'SLUG': t['slug'], 'MAIN': t['main'],
               'SRC_ROOT': SRC_ROOT, 'BUILD': BUILD,
               'progmem_const': progmem_const}
        code = compile(open(fx, encoding='utf-8').read(), fx, 'exec')
        exec(code, env)


def compile_one(t, worker):
    slug = t['slug']
    log_path = os.path.join(LOGS, slug + '.log')
    res = {'slug': slug, 'top': t['top'], 'entry': t['entry'], 'ok': False}

    # a few entries ship only as a prebuilt .hex from their own author
    if t.get('use_prebuilt'):
        src = os.path.join(SRC_ROOT, t['use_prebuilt'])
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(HEXOUT, slug + '.hex'))
            res.update(ok=True, source='prebuilt', prebuilt=t['use_prebuilt'])
        else:
            res['error'] = 'prebuilt hex not found: ' + src
        return res

    try:
        ino = stage(t)
    except Exception as exc:
        res['error'] = 'stage failed: %r' % (exc,)
        open(log_path, 'w', encoding='utf-8').write(res['error'])
        return res

    # build path is per-process as well as per-worker so that several agents
    # can drive this script at the same time without trampling each other
    bp = os.path.join(BPROOT, 'p%d_w%d' % (os.getpid(), worker))
    shutil.rmtree(bp, ignore_errors=True)
    os.makedirs(bp, exist_ok=True)

    libs = [os.path.join(ARDUINO, 'portable', 'sketchbook', 'libraries')]
    if os.path.isdir(EXTRA_LIBS):
        libs.insert(0, EXTRA_LIBS)
    # A sketch that vendors its own libraries/ folder gets it too. Search for
    # it rather than deriving the path: staging renames the sketch directory to
    # match its main .ino, and for the many repos whose sketch sits at the top
    # level that renames the game root along with it.
    stage_root = os.path.join(STAGE, slug)
    for depth_root, dirnames, _files in os.walk(stage_root):
        if depth_root[len(stage_root):].count(os.sep) > 2:
            dirnames[:] = []
            continue
        for d in dirnames:
            if d.lower() in ('libraries', 'lib'):
                libs.insert(0, os.path.join(depth_root, d))

    cmd = [os.path.join(ARDUINO, 'arduino-builder.exe'), '-compile',
           '-hardware', os.path.join(ARDUINO, 'hardware'),
           '-hardware', os.path.join(ARDUINO, 'portable', 'packages'),
           '-tools', os.path.join(ARDUINO, 'tools-builder'),
           '-tools', os.path.join(ARDUINO, 'hardware', 'tools', 'avr'),
           '-tools', os.path.join(ARDUINO, 'portable', 'packages'),
           '-built-in-libraries', os.path.join(ARDUINO, 'libraries'),
           '-fqbn=' + FQBN,
           '-build-path', bp,
           '-warnings=none']
    for l in libs:
        cmd += ['-libraries', l]
    cmd.append(ino)

    def run_builder():
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                               errors='replace')
            return p.stdout + '\n' + p.stderr, p.returncode
        except subprocess.TimeoutExpired:
            return 'TIMEOUT after 600s', -9

    t0 = time.time()
    out, rc = run_builder()
    # Under heavy parallelism arduino-builder occasionally exits non-zero with
    # no diagnostic at all (a transient file lock, not a code problem). A real
    # compile error always names itself, so retry only the silent ones.
    if rc != 0 and 'error' not in out.lower():
        res['retried'] = True
        shutil.rmtree(bp, ignore_errors=True)
        os.makedirs(bp, exist_ok=True)
        time.sleep(2)
        out, rc = run_builder()
    res['seconds'] = round(time.time() - t0, 1)

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(' '.join(cmd) + '\n\n' + out)

    stem = os.path.splitext(os.path.basename(ino))[0]
    hexf = os.path.join(bp, stem + '.ino.hex')
    if rc == 0 and os.path.isfile(hexf):
        shutil.copyfile(hexf, os.path.join(HEXOUT, slug + '.hex'))
        res['ok'] = True
        for line in out.splitlines():
            if 'program storage space' in line:
                res['size'] = line.strip()
            if 'dynamic memory' in line:
                res['ram'] = line.strip()
    else:
        res['rc'] = rc
        tail = [l for l in out.splitlines() if l.strip()][-6:]
        res['error'] = '\n'.join(tail)
    return res


def main():
    targets = json.load(open(os.path.join(BUILD, 'targets.json')))
    only = set(sys.argv[1:])
    if only:
        targets = [t for t in targets if t['slug'] in only]
    targets = [t for t in targets if t.get('main') or t.get('use_prebuilt')]

    for d in (STAGE, HEXOUT, LOGS, BPROOT, RESULTS):
        os.makedirs(d, exist_ok=True)

    q = queue.Queue()
    for t in targets:
        q.put(t)
    results = []
    lock = threading.Lock()

    def worker(wid):
        while True:
            try:
                t = q.get_nowait()
            except queue.Empty:
                return
            r = compile_one(t, wid)
            with lock:
                results.append(r)
                print(('  OK  ' if r['ok'] else 'FAIL  ') + r['slug'] +
                      ('' if r['ok'] else '  rc=%s' % r.get('rc')), flush=True)

    n = min(8, (os.cpu_count() or 4))
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    t0 = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    results.sort(key=lambda r: r['slug'].lower())
    # one file per target, so concurrent runs never race on a shared report
    os.makedirs(RESULTS, exist_ok=True)
    for r in results:
        json.dump(r, open(os.path.join(RESULTS, r['slug'] + '.json'), 'w'), indent=1)

    shutil.rmtree(os.path.join(BPROOT, 'p%d_w0' % os.getpid()), ignore_errors=True)

    ok = sum(1 for r in results if r['ok'])
    print('\n%d/%d compiled in %.0fs' % (ok, len(results), time.time() - t0))
    failed = [r['slug'] for r in results if not r['ok']]
    if failed:
        print('FAILED:', ', '.join(failed))


if __name__ == '__main__':
    main()
