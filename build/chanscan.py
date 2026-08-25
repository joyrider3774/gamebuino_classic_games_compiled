"""Work out how many sound channels each sketch actually needs.

Gamebuino Classic's library ships `#define NUM_CHANNELS 1` in utility/settings.c,
and Sound::playTrack/playPattern silently `return` when the channel index is
>= NUM_CHANNELS. A game that plays its music on channel 1 or 2 therefore builds
and runs fine but is simply mute, while its channel-0 effects still work.
"""
import os, re, json

BUILD = r"C:\gbbuild"
SRC_ROOT = r"C:\github\gamebuino_classic_source_codes"
EXT = ('.ino', '.pde', '.h', '.hpp', '.c', '.cpp')

# channel is the LAST argument of these
LAST_ARG = ('playTrack', 'playPattern', 'changePatternSet', 'changeInstruments',
            'setPatternSpeed')
# channel is the ONLY argument of these
ONLY_ARG = ('stopTrack', 'stopPattern')

CALL = re.compile(r'\bsound\s*\.\s*(\w+)\s*\(')


def split_args(text, i):
    """Split the argument list of a call whose '(' is at text[i]."""
    depth, args, cur = 0, [], ''
    while i < len(text):
        c = text[i]
        if c in '([':
            depth += 1
            if depth == 1:
                i += 1
                continue
        elif c in ')]':
            depth -= 1
            if depth == 0:
                args.append(cur)
                return args
        if depth == 1 and c == ',':
            args.append(cur)
            cur = ''
        else:
            cur += c
        i += 1
    return args


def scan(path):
    """max channel index used, and whether any channel arg was not a literal"""
    hi, dynamic = -1, False
    try:
        t = open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return hi, dynamic
    t = re.sub(r'//[^\n]*', '', t)
    t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
    for m in CALL.finditer(t):
        fn = m.group(1)
        if fn not in LAST_ARG and fn not in ONLY_ARG:
            continue
        args = split_args(t, m.end() - 1)
        if not args:
            continue
        if fn in ONLY_ARG and len(args) != 1:
            continue          # the no-arg stopTrack() overload stops everything
        a = args[-1].strip()
        if re.fullmatch(r'\d+', a):
            hi = max(hi, int(a))
        elif a:
            dynamic = True
    return hi, dynamic


def main():
    targets = {t['slug']: t for t in json.load(open(os.path.join(BUILD, 'targets.json')))}
    out = {}
    for slug, t in sorted(targets.items()):
        if not t.get('sketch_rel'):
            continue
        # read the archive directly, so this can run before anything is staged
        d = os.path.join(SRC_ROOT, t['sketch_rel'])
        if not os.path.isdir(d):
            continue

        hi, dynamic = -1, False
        for dp, dn, fs in os.walk(d):
            dn[:] = [x for x in dn if x not in ('.git', 'libraries', 'lib')]
            for f in fs:
                if f.lower().endswith(EXT):
                    h, dy = scan(os.path.join(dp, f))
                    hi = max(hi, h)
                    dynamic |= dy
        if hi >= 1 or dynamic:
            out[slug] = {'max_channel': hi, 'dynamic': dynamic,
                         'needs': max(hi + 1, 2 if dynamic else 1)}

    for slug, v in sorted(out.items(), key=lambda kv: -kv[1]['needs']):
        print('%-34s highest channel used: %-3s %s-> NUM_CHANNELS %d'
              % (slug, v['max_channel'] if v['max_channel'] >= 0 else '?',
                 'computed index ' if v['dynamic'] else '', v['needs']))
    print('\n%d of %d sketches use a sound channel above 0' % (len(out), len(targets)))
    json.dump(out, open(os.path.join(BUILD, 'channels.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
