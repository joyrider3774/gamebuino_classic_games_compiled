"""gruniozerca-gamebuino: drop the alternative-language second program.

The repository root *is* the sketch folder, and it holds two complete,
self-contained versions of the same game as two separate .ino tabs:

    gruniozerca.ino      -- Polish version   (-> GRUNIO.HEX)
    gruniozerca-en.ino   -- English version  (-> GRUNIOEN.HEX)
    arhn.ino             -- the custom 3x5 font, shared by both

The project README says exactly that: "You can open the gruniozerca.ino
(Polish version) or gruniozerca-en.ino (English version) of the files in
the Arduino IDE".  They were never meant to be compiled together -- but
the Arduino builder concatenates every .ino in the folder, so `Gamebuino
gb`, every sprite, every global and finally setup()/loop() are all
defined twice: "error: redefinition of 'void loop()'".

targets.json selects gruniozerca.ino as the main tab, so this fix-up
removes the English twin from the *staged* copy only.  arhn.ino is kept:
it is the shared font, not an alternative program.  The result is the
Polish build, i.e. the released GRUNIO.HEX.
"""
import os

for fn in ('gruniozerca-en.ino',):
    p = os.path.join(SKETCH_DIR, fn)
    if os.path.isfile(p):
        os.remove(p)
