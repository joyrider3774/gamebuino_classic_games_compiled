r"""gamebuino-community-rpg: revert the sound calls to the stock-library form.

Two separate problems in this target:

1. <GB_Fat.h> -- Sorunome's own tiny read-only FAT library, never bundled
   with the game.  Recovered from https://github.com/Sorunome/GB_Fat and
   vendored at C:\gbbuild\libs\GB_Fat (no fix-up needed for that part).

2. Upstream commit 448e764 "sound optimization thing" (2016-04-06) moved the
   soundbuffer addresses *into a locally patched copy of the Gamebuino
   library* that was never published:

       -  gb.sound.playTrack((const uint16_t *)(SOUNDBUFFER_OFFSET),0);
       -  gb.sound.playTrack((const uint16_t *)(SOUNDBUFFER_OFFSET + 40),1);
       +  gb.sound.playTrack(0);
       +  gb.sound.playTrack(1);
       -  gb.sound.changePatternSet((const uint16_t* const*)(SOUNDBUFFER_OFFSET+80), 0);   (and ch 1)

   Against the stock Gamebuino_Classic 0.5.2 the one-argument playTrack does
   not exist, so the build dies with "no matching function for call to
   Sound::playTrack(int)".

   The author left the pre-448e764 lines in place as comments, so the fix is
   simply to revert his optimisation in the *staged* copy: drop the one-arg
   calls and un-comment his own two-arg originals (playTrack in util.cpp,
   changePatternSet in the main .ino).  The patched library only inlined
   those very constants, so the resulting program is the same program.
"""
import os, re

# 1) delete the one-argument playTrack() calls that need the patched library
DROP_1ARG = re.compile(r'^[ \t]*gb\.sound\.playTrack\([01]\);.*\r?\n', re.M)
# 2) restore the author's own commented-out stock-library calls
UNCOMMENT = re.compile(r'^([ \t]*)//(gb\.sound\.(?:playTrack|changePatternSet)\()', re.M)


def patch(path):
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8', errors='surrogateescape', newline='') as f:
        src = f.read()
    out = UNCOMMENT.sub(r'\1\2', DROP_1ARG.sub('', src))
    if out != src:
        with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
            f.write(out)


patch(os.path.join(SKETCH_DIR, 'util.cpp'))
patch(os.path.join(SKETCH_DIR, MAIN))


# 3) avr-gcc 7.3 / LTO inlines sprite_xor() into drawTilemap(), which needs Y
#    (r28/r29) as its frame pointer -- the hand-written asm block also demands
#    Y via its "y" constraint, so the allocator gives up with
#      "can't find a register in class 'POINTER_Y_REGS' while reloading 'asm'".
#    The 2016 compiler kept these out of line.  noinline restores that and is a
#    pure code-generation hint: the emitted code is the author's own asm.
NOINLINE = re.compile(r'^void (sprite_xor|sprite_masked)\(byte data\[\]', re.M)


def add_noinline(path):
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8', errors='surrogateescape', newline='') as f:
        src = f.read()
    out = NOINLINE.sub(r'void __attribute__((noinline)) \1(byte data[]', src)
    if out != src:
        with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
            f.write(out)


add_noinline(os.path.join(SKETCH_DIR, 'graphics.cpp'))
