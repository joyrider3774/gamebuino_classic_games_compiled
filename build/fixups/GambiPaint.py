"""GambiPaint: drop the stale Arduino build artefact that shadows the sketch.

The repo ships GambiPaint.ino (the real, commented source) *and*
GambiPaint.cpp + GambiPaint.cpp.elf, which are leftovers from an old
Arduino IDE build: GambiPaint.cpp starts with `#line 1 "GambiPaint.ino"`,
carries the prototypes the IDE auto-injects, and is otherwise the .ino with
every comment blanked out.  arduino-builder compiles both, so every global
and every function (setup, loop, menuLoop, brushBigs, ...) is defined twice
and the link fails with "multiple definition of ...".

Verified before removing: with comments, #line directives and the injected
prototype block normalised away, the two files are identical apart from one
insignificant whitespace difference, so deleting the .cpp loses no code.
The .ino is kept as the source of truth.
"""
import os

for stale in ("GambiPaint.cpp", "GambiPaint.cpp.elf"):
    p = os.path.join(SKETCH_DIR, stale)
    if os.path.isfile(p):
        os.remove(p)
