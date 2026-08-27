# CHIP-8 ROMs on the card image

`tools/chip-8-gamebuino` is a CHIP-8 interpreter, not a game: it lists the SD
card root and offers any file whose name ends in `8` as a ROM. With an empty
card it has nothing to run, so these five programs are written onto
`webemulator/sdcard.img` by `build/mksd.py` (alongside `DEMO.CH8`, which is
generated in that script rather than taken from anywhere).

**None of these are Gamebuino software** and none of them come from the
`gamebuino_classic_source_codes` archive. They are CHIP-8 programs from the
1970s-90s, written for the COSMAC VIP and later for the HP-48 CHIP-48
interpreter, and they are here only so the interpreter has something to
interpret. They are listed separately for that reason.

| File | Program | Author | Year | Keys used |
| --- | --- | --- | --- | --- |
| `BRIX.CH8` | Brix | Andreas Gustafsson | 1990 | 4, 6 |
| `INVADERS.CH8` | Space Invaders | David Winter | 199x | 4, 5, 6 |
| `BLITZ.CH8` | Blitz | David Winter | 199x | 5 |
| `PONG1.CH8` | Pong (1 player) | Paul Vervalin (Pong, 1990), one-player hack unattributed | 1990 | 1, 4 |
| `TETRIS.CH8` | Tetris | Fran Dachille | 1991 | 1, 4, 5, 6 |

All five use six keys or fewer, which matters: the sketch lets you bind exactly
six CHIP-8 keys to the Gamebuino's six buttons, and stores the binding in
EEPROM. Nothing here needs a key you cannot reach.

## Where they came from

Taken verbatim from the *Chip-8 Program Pack* (RS-C8000, Revival Studios,
2011-04-16), a compilation of CHIP-8 programs collected from the web with
authorship and dates researched and recorded per ROM. Its README states: *"This
package can be freely distributed in its original form."* Fetched from
<https://github.com/kripod/chip8-roms>, which republishes that pack.

Two notes on the individual programs, from the pack's own per-ROM text files:

* David Winter's CHIP-8 games have circulated as freely distributable since his
  original CHIP8 emulator package.
* Tetris ships with a note from Fran Dachille asking anyone who enjoys it to
  send $5 in support of further versions. That is a request for voluntary
  support, not a charge for copies; the address in it is from 1991 and the
  program has been redistributed in every CHIP-8 pack since. It is included on
  that basis, and the note is repeated here so the ask is not lost.

If any author would rather their program were not shipped here, it can be
dropped from `ROMS` in `build/mksd.py` and the image rebuilt.

## Checksums

```
8180b836eeb629ba93583519a5fb7b38  BLITZ.CH8
d677c1b9de941484d718799aebafebf3  BRIX.CH8
a67f58742cff77702cc64c64413dc37d  INVADERS.CH8
d7c0a76147c5f16bb498aa410f1f21f2  PONG1.CH8
aef4fc8c2a5e8431f5e0736ab281f2ee  TETRIS.CH8
```
