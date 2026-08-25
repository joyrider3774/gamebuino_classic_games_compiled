# Bomber: avr-gcc 7.3 requires PROGMEM data to be const.
# Maze5 is the only level table left non-const in Maze.ino (Maze1..Maze4
# already are). It is read only through loadMaze(const byte*)/pgm_read_byte,
# so const is safe and keeps it in flash.
import os, re, io

p = os.path.join(SKETCH_DIR, 'Maze.ino')
s = io.open(p, encoding='utf-8', errors='replace').read()
new = re.sub(r'(?m)^(\s*)byte(\s+Maze5\s*\[)', r'\1const byte\2', s)
if new != s:
    io.open(p, 'w', encoding='utf-8', newline='').write(new)
