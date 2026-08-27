r"""Flabuino never initialises the Gamebuino library.

`Flabuino.ino`'s setup() calls `game.init()`, and `Game::init()` (Game.cpp)
only calls `flappy.init()` -- `gb.begin()` is called nowhere in the repository.
Without it the library never sets up the Nokia 5110 panel, so nothing is ever
drawn; that is true on real hardware too, not just under the emulator.

Add the missing call at the top of Game::init(), which is where the game's own
initialisation already happens and where `gb` is in scope (it is a member of
Game). Nothing else is changed.
"""
import os, re

p = os.path.join(SKETCH_DIR, 'Game.cpp')
with open(p, encoding='utf-8', errors='surrogateescape') as f:
    t = f.read()

old = 'void Game::init() {\n  flappy.init();'
new = ('void Game::init() {\n'
       '  gb.begin();   // missing upstream: without it the display is never set up\n'
       '  flappy.init();')

if 'gb.begin()' not in t:
    assert t.count(old) == 1, 'Game::init() is not in the expected shape'
    t = t.replace(old, new, 1)
    with open(p, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(t)
