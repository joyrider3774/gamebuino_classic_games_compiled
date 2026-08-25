r"""The Snake folder of the StijnCaerts-Gamebuino repo holds two independent
sketches: SnakeStart.ino (a 51-line first iteration) and Snake2.ino (the
finished one, which is this target's main sketch).  The Arduino builder
concatenates every .ino in the sketch folder, so SnakeStart.ino collides with
Snake2.ino (duplicate class Coordinate, positions, gb, setup(), loop()).
Drop the earlier iteration from the staged copy; Snake2.ino is self-contained.

The <LinkedList.h> the sketch needs (ivanseidel/LinkedList, named in its own
header comment) is vendored in C:\gbbuild\libs\LinkedList.
"""
import os

stray = os.path.join(SKETCH_DIR, 'SnakeStart.ino')
if os.path.isfile(stray):
    os.remove(stray)
