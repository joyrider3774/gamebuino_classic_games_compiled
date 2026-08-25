r"""Wolfenduino keeps its engine outside the sketch folder.

The repository is a multi-platform raycaster: the portable engine lives in
Game/, its generated data tables in DataHeaders/, and each target gets a thin
folder of its own (Gamebuino/, Uzebox/, Windows/, ...). The author's own builds
add those directories to the include path, but the Arduino IDE only compiles
what sits in the sketch folder, so `#include "Engine.h"` cannot resolve.

Two further changes:

* PROGMEM tables need to be const, including the menu and audio *pointer*
  arrays -- their elements were already const but the arrays themselves were
  not.
* `gb.display.autoUpdate` does not exist in Gamebuino Classic 0.5.2. The sketch
  clears it so that `gb.update()` will not push the framebuffer before
  `engine.draw()` has filled it; without the flag the library pushes on every
  `gb.update()` as well as on the sketch's own `gb.display.update()` at the end
  of the loop. The frame the sketch draws is still the one that lands last, so
  the picture is right -- it just costs an extra SPI transfer per frame.
"""
import os, re, shutil

for src in ('Game', 'DataHeaders'):
    d = os.path.join(GAME_ROOT, src)
    if not os.path.isdir(d):
        continue
    for fn in os.listdir(d):
        if fn.lower().endswith(('.h', '.hpp', '.c', '.cpp')):
            dst = os.path.join(SKETCH_DIR, fn)
            if not os.path.exists(dst):
                shutil.copyfile(os.path.join(d, fn), dst)

progmem_const(SKETCH_DIR)

main = os.path.join(SKETCH_DIR, os.path.splitext(MAIN)[0] + '.ino')
with open(main, encoding='utf-8', errors='surrogateescape') as f:
    t = f.read()
new = re.sub(r'^(\s*)(gb\.display\.autoUpdate\s*=.*)$',
             r'\1// \2  // no such member in Gamebuino Classic 0.5.2',
             t, flags=re.MULTILINE)
if new != t:
    with open(main, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(new)

# The definitions above are now const; their extern declarations have to agree,
# or gcc reports a conflicting redeclaration.
DECL = re.compile(r'^(\s*extern\s+.*\*)\s*(\w+)\s*(\[[^\]]*\]\s*;)', re.MULTILINE)
for dirpath, dirnames, filenames in os.walk(SKETCH_DIR):
    dirnames[:] = [d for d in dirnames if d.lower() != '.git']
    for fn in filenames:
        if not fn.lower().endswith(('.h', '.hpp')):
            continue
        fp = os.path.join(dirpath, fn)
        with open(fp, encoding='utf-8', errors='surrogateescape') as f:
            t = f.read()
        new = DECL.sub(lambda m: m.group(0) if re.search(r'\*\s*const\s*$', m.group(1) + ' ')
                       else m.group(1) + ' const ' + m.group(2) + m.group(3), t)
        if new != t:
            with open(fp, 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(new)
