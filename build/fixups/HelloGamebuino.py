# HelloGamebuino ships its sketch as hello.cpp, built by CMake + avr-gcc
# rather than by the Arduino IDE. The file is already a plain Arduino sketch
# (setup/loop, #include <Gamebuino.h>) so it just needs the .ino name the
# Arduino builder expects. The CMake scaffolding is dropped from the staged
# copy so the builder does not try to treat it as sketch content.
import os

src = os.path.join(SKETCH_DIR, 'hello.cpp')
dst = os.path.join(SKETCH_DIR, 'HelloGamebuino.ino')
if os.path.isfile(src) and not os.path.isfile(dst):
    os.rename(src, dst)

for junk in ('CMakeLists.txt', 'gamebuino.cmake', 'Makefile'):
    p = os.path.join(SKETCH_DIR, junk)
    if os.path.isfile(p):
        os.remove(p)
