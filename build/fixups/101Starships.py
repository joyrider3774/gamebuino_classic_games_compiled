"""101Starships: revive the 2013-era `prog_uchar` PROGMEM table.

`ennemiSet` (the enemy-wave table) is declared in the main tab as

    PROGMEM  prog_uchar ennemiSet[]  = { ... };

`prog_uchar` was removed from avr-libc in 2012 (deprecated) and no longer
exists in the toolchain shipped with Arduino 1.8.19, so the declaration is
not a type at all.  Everything downstream -- the main tab's own use at
line 530 and every use in ennemis.ino -- then reports
"'ennemiSet' was not declared in this scope".  It is a single cascading
error, not a tab-ordering problem.

The faithful modern spelling of `PROGMEM prog_uchar x[]` is
`const unsigned char x[] PROGMEM` -- same storage (flash), same element
type, same `pgm_read_byte_near()` access.  Nothing else changes.
"""
import os, re

DECL_PTR = re.compile(
    r'PROGMEM\s+prog_uchar\s*\*\s*(\w+)\s*\[\s*\]\s*(?:PROGMEM\s*)?=')
DECL_ARR = re.compile(
    r'PROGMEM\s+prog_uchar\s+(\w+)\s*\[\s*\]\s*(?:PROGMEM\s*)?=')


def fix(text):
    text = DECL_PTR.sub(lambda m: 'const unsigned char * const %s[] PROGMEM =' % m.group(1), text)
    text = DECL_ARR.sub(lambda m: 'const unsigned char %s[] PROGMEM =' % m.group(1), text)
    # anything left (plain pointer/local declarations) is just the old typedef
    text = re.sub(r'\bprog_uchar\b', 'const unsigned char', text)
    return text


for fn in sorted(os.listdir(SKETCH_DIR)):
    if not fn.lower().endswith(('.ino', '.pde', '.h', '.hpp', '.c', '.cpp')):
        continue
    p = os.path.join(SKETCH_DIR, fn)
    with open(p, 'r', encoding='utf-8', errors='surrogateescape', newline='') as f:
        src = f.read()
    if 'prog_uchar' not in src:
        continue                      # idempotent: nothing left to do
    out = fix(src)
    if out != src:
        with open(p, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
            f.write(out)
