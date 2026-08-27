r"""ChuckieGameBuino ships its sketch as chuckie.c.

The file is already a plain Arduino sketch -- `#include <SPI.h>`,
`#include <Gamebuino.h>`, `setup()` and `loop()` -- so it only needs the .ino
name the Arduino builder expects. Its logo table also has to become const, as
avr-gcc has required of PROGMEM data since 4.6.
"""
import os

src = os.path.join(SKETCH_DIR, 'chuckie.c')
dst = os.path.join(SKETCH_DIR, os.path.splitext(MAIN)[0] + '.ino')
if os.path.isfile(src) and not os.path.isfile(dst):
    os.rename(src, dst)

progmem_const(SKETCH_DIR)
