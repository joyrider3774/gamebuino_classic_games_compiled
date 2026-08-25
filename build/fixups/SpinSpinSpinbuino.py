"""SpinSpinSpinbuino: revive the 2013-era `prog_uchar` / non-const PROGMEM decls.

Root cause is the same single cascading error as 101Starships: the two
globals that hold the level pointers are declared in the main tab as

    prog_uchar* current_level;
    prog_uchar* current_settings;

`prog_uchar` no longer exists in the avr-libc that ships with Arduino
1.8.19, so those two lines do not declare anything and every later use in
Joueur.ino / collisions.ino / niveaux.ino reports
"'current_settings' was not declared in this scope".

Two further declarations are rejected by modern avr-gcc for a related
reason -- since gcc 4.6 a PROGMEM variable must be const:

    PROGMEM prog_uchar *niveaux[]        (niveaux.ino)
    const byte *ressorts[] PROGMEM       (bitmaps.ino)

The 2013 toolchain forced the `progmem` attribute to imply read-only,
which is why these compiled *and* why gcc constant-folded every
`niveaux[n]` / `ressorts[n]` read into the flash address of the target
table.  That folding is what makes the game work -- the released
SPINSPIN.HEX shows the tables sitting in flash (niveaux at 0x0901,
ressorts at 0x0086) while the use sites load the target addresses as
plain immediates (e.g. `ldi r18,0x21 / ldi r19,0x09` = &ressort0).
Adding the `const` that the modern compiler asks for restores exactly
that: the tables stay in flash and every constant-index read folds again.

Transformations (all idempotent):
  PROGMEM prog_uchar  x[] [PROGMEM] =  ->  const unsigned char x[] PROGMEM =
  PROGMEM prog_uchar *x[] [PROGMEM] =  ->  const unsigned char * const x[] PROGMEM =
  leftover `prog_uchar`               ->  const unsigned char
  const byte *ressorts[] PROGMEM      ->  const byte * const ressorts[] PROGMEM
"""
import os, re

DECL_PTR = re.compile(
    r'PROGMEM\s+prog_uchar\s*\*\s*(\w+)\s*\[\s*\]\s*(?:PROGMEM\s*)?=')
DECL_ARR = re.compile(
    r'PROGMEM\s+prog_uchar\s+(\w+)\s*\[\s*\]\s*(?:PROGMEM\s*)?=')
# array-of-pointers-to-PROGMEM-bitmap that is itself in PROGMEM but not const
PTR_TABLE = re.compile(
    r'const\s+byte\s*\*\s*(?!const\b)(\w+)\s*\[\s*\]\s*PROGMEM')


def fix(text):
    text = DECL_PTR.sub(lambda m: 'const unsigned char * const %s[] PROGMEM =' % m.group(1), text)
    text = DECL_ARR.sub(lambda m: 'const unsigned char %s[] PROGMEM =' % m.group(1), text)
    text = re.sub(r'\bprog_uchar\b', 'const unsigned char', text)
    text = PTR_TABLE.sub(lambda m: 'const byte * const %s[] PROGMEM' % m.group(1), text)
    return text


for fn in sorted(os.listdir(SKETCH_DIR)):
    if not fn.lower().endswith(('.ino', '.pde', '.h', '.hpp', '.c', '.cpp')):
        continue
    p = os.path.join(SKETCH_DIR, fn)
    with open(p, 'r', encoding='utf-8', errors='surrogateescape', newline='') as f:
        src = f.read()
    out = fix(src)
    if out != src:
        with open(p, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
            f.write(out)
