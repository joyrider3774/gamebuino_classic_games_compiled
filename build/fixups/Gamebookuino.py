r"""Gamebookuino targets a pre-1.8 avr-libc.

Two mechanical changes:

1. `prog_char` was deprecated in avr-libc 1.8 and deleted afterwards. The modern
   spelling is a plain `char` in a PROGMEM object, and `strncat_P` already takes
   a `const char*`.
2. Its menu tables are declared `PROGMEM const char* name[]`, which avr-gcc now
   rejects: the array of pointers itself has to be const too.

The game ships its own patched copy of the Gamebuino library (it adds the
`popup(const char*, uint8_t)` overload the code calls), which build.py relocates
onto the library search path, so it builds against the author's library rather
than the installed one.
"""
import os, re

PROG_CHAR = re.compile(r'\bprog_char\b')

for dirpath, dirnames, filenames in os.walk(SKETCH_DIR):
    dirnames[:] = [d for d in dirnames if d.lower() != '.git']
    for fn in filenames:
        if not fn.lower().endswith(('.ino', '.h', '.hpp', '.c', '.cpp')):
            continue
        p = os.path.join(dirpath, fn)
        with open(p, encoding='utf-8', errors='surrogateescape') as f:
            t = f.read()
        new = PROG_CHAR.sub('char', t)
        if new != t:
            with open(p, 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(new)

progmem_const(SKETCH_DIR)
