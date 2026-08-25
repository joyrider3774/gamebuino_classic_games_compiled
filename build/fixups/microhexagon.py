# microhexagon: avr-gcc 7.3 requires PROGMEM data to be const.
#
# wallsData.h holds the wall/pattern tables (patt1..patt6, du and the
# _pattern descriptors pattern1..pattern6, dummy). They are only ever read
# through pgm_read_*_near(), so they can all be const and stay in flash.
#
# Knock-on: _pattern::walls must become 'const wall *' (it points at the
# now-const PROGMEM wall arrays), patternList[] must hold pointers to const,
# and storePattern() must take a 'const struct _pattern *' and cast the
# pgm_read_word_near() result to 'const wall *'.
import os, re, io


def rewrite(path, subs):
    if not os.path.isfile(path):
        return
    s = io.open(path, encoding='utf-8', errors='replace').read()
    new = s
    for pat, rep in subs:
        new = re.sub(pat, rep, new)
    if new != s:
        io.open(path, 'w', encoding='utf-8', newline='').write(new)


# --- the PROGMEM tables themselves -----------------------------------------
rewrite(os.path.join(SKETCH_DIR, 'wallsData.h'), [
    # wall pattN[] PROGMEM = ... / wall du[] PROGMEM = ...
    (r'(?m)^(?![ \t]*const\b)([ \t]*)wall(\s+\w+\s*\[\s*\]\s*PROGMEM)',
     r'\1const wall\2'),
    # _pattern patternN PROGMEM = ... / _pattern dummy PROGMEM = ...
    (r'(?m)^(?![ \t]*const\b)([ \t]*)_pattern(\s+\w+\s+PROGMEM)',
     r'\1const _pattern\2'),
    # the lookup table now holds pointers to const _pattern
    (r'(?m)^(?![ \t]*const\b)([ \t]*)_pattern(\s*\*\s*patternList\s*\[)',
     r'\1const _pattern\2'),
])

# --- struct member has to point at const flash data -------------------------
rewrite(os.path.join(SKETCH_DIR, 'walls.h'), [
    (r'(?m)^(?![ \t]*const\b)([ \t]*)wall(\s*\*\s*walls\s*;)',
     r'\1const wall\2'),
    # keep the (unused) by-value overload declaration consistent
    (r'void\s+storePattern\s*\(\s*_pattern\s+origin\s*,',
     'void storePattern(const _pattern origin,'),
])

# --- the reader ------------------------------------------------------------
rewrite(os.path.join(SKETCH_DIR, 'walls.ino'), [
    (r'void\s+storePattern\s*\(\s*struct\s+_pattern\s*\*\s*origin\s*,',
     'void storePattern(const struct _pattern *origin,'),
    (r'dest->walls\s*=\s*\(\s*wall\s*\*\s*\)', 'dest->walls = (const wall*)'),
])
