# Gamebuino Classic — playable in your browser

Every [Gamebuino Classic](https://gamebuino.com/) game and tool whose source
could still be found, compiled from that source and running in the browser on
Mark Feldman's [Simbuino](https://github.com/Myndale/Simbuino) HTML5 emulator.

The Gamebuino Classic was a small hobbyist open-source handheld: an ATmega328
at 16 MHz, 2 KB of RAM, 32 KB of flash, and an 84×48 Nokia 5110 monochrome LCD.
Its community wiki, and most of the forum threads and personal sites it linked
to, are long gone from the live web.

**Open [`index.html`](index.html)** — or serve this folder over HTTP — for the
grid of every game, with search and a play-in-place window.

Nothing here is my own work. Every entry is someone else's game or tool, kept
under its own author's own licence; see each card on the page, and the
[source archive](https://github.com/joyrider3774/gamebuino_classic_source_codes)
for the full licence notes.

## What's in here

| Path | What it is |
|---|---|
| [`index.html`](index.html) | The collection page — 137 games, 20 tools |
| [`games/`](games/) | One compiled `.hex` per game |
| [`tools/`](tools/) | One compiled `.hex` per non-game tool |
| [`screenshots/`](screenshots/) | One 336×192 PNG per entry, captured from the emulator |
| [`webemulator/`](webemulator/) | The standalone Simbuino4Web player |
| [`build/`](build/) | The build harness: discovery, compile, per-game fix-ups, screenshots, page generation |

## The emulator

[Simbuino4Web](https://github.com/Myndale/Simbuino/tree/master/src/Simbuino4Web)
is a cycle-level ATmega328 emulator written in plain JavaScript, plus emulation
of the Nokia 5110 LCD, the buttons, the speaker and an SPI SD card. Upstream it
ships as an ASP.NET MVC application whose only way to load a game is a file
picker, so `webemulator/` is a standalone rebuild of it:

- `webemulator/js/` — the emulator core, taken from upstream with four fixes
  and one feature ported from Simbuino's standalone C# emulator:
  - `AtmelContext.js` — `UpdateInterruptFlags()` tested a bare `SREG`, which is
    undefined in the port (everywhere else it writes `AtmelContext.SREG`). It
    threw a `ReferenceError` out of the frame loop, freezing any sketch that
    reached that path — sokobuino's own released `.hex` stalls on frame 1
    without it.
  - `AtmelProcessor.js` — `ASR` sign-extends its operand before shifting, so
    the result is negative for any input >= 128. The port stored it into the
    register file unmasked, leaving a negative number in an array the flag
    lookup tables are indexed by. This is what stopped **cruiser** rendering.
  - `AtmelProcessor.js` — `MULSU` multiplies a *signed* operand by an
    *unsigned* one, but the port sign-extended both, so the product was wrong
    whenever the second operand was >= 128. avr-gcc emits `MULSU` inside its
    16×16 signed multiply helpers, so this affected fixed-point arithmetic.
    Nearly every entry executes `MULSU` — 116 of the 119 present when this was
    measured — though only two were measurably affected by the bug itself
    (Super Crate Buino, Community RPG).
  - `SdDevice.js` — reads a byte past the end of a card image as `0` instead of
    clocking `undefined` out over SPI, so a card image can be stored trimmed of
    its trailing empty space.
  - `Lcd.js` — the **grey blend**, ported from the standalone's Persistence
    option. The library draws `GRAY` as a checkerboard that inverts every
    frame (`(x ^ y ^ frameCount) & 1`), so on a one-bit panel it only reads as
    a mid-tone once the LCD's response time is simulated; otherwise it
    shimmers, and a screenshot catches whichever phase the frame held. 15
    entries use `GRAY`. It is **on** by default here (upstream defaults it
    off); the player has a *Grey blend* toggle, `?gray=0` disables it for one
    link, and the choice is remembered per browser.

  Simbuino ships two emulators that do **not** share code — a C# desktop
  application and this JavaScript port — and the port has drifted from the C#
  core. Both the `SREG` and `MULSU` fixes simply make the JavaScript behave the
  way the C# already does. [`webemulator/upstream/`](webemulator/upstream/)
  holds byte-exact copies of the three modified files plus the complete patch,
  and records what else was compared between the two cores.
- `webemulator/player.js` — replaces upstream's `Simulation.js`. Same emulator
  lifecycle, but it loads a game from the URL, adds arrow keys and on-screen
  touch controls, and exposes a small hook the screenshot tool drives.
- `webemulator/player.html` — the page itself.

Two files upstream's own `Index.cshtml` references, `Deltas.js` and
`PortRegister.js`, do not exist in the repository or in its prebuilt zip. They
are stale references: `PortRegister` is defined inside `AtmelRegisters.js` and
nothing refers to `Deltas` at all.

Link a game directly with `webemulator/player.html?hex=<url>`, plus optional
`&title=<name>` and `&sd=<url of a raw card image>`.

### Controls

| Key | Button |
|---|---|
| Arrows, or `E`/`S`/`D`/`F` | D-pad |
| `X` or `K` | A |
| `Z` or `L` | B |
| `C` or `R` | C |

Most games open on a title screen and start with **A**. On a touch device,
on-screen buttons appear instead.

## How the games were built

Source comes from
[gamebuino_classic_source_codes](https://github.com/joyrider3774/gamebuino_classic_source_codes),
which files its finds in four categories: `games/` (111) and `tools/` (17) hold
entries with real source, and `games_precompiled/` (25) and `tools_precompiled/`
(6) hold ones where only a compiled binary survives. That yields 157 entries
here because:

- `StijnCaerts-Gamebuino` holds **two** separate games (Pong and Snake), so it
  splits into two entries.
- Three folders are deliberately left out. `Gamebuino-Classic-Games-Compilation`
  and `Gamebuino-Classic_Games` are not programs: they are ready-made SD cards
  bundling 50 and 141 prebuilt `.HEX` files, and the individual titles mined out
  of them are exactly what the `games_precompiled/` category now holds.
  `gamebuinoEducation` is a teaching course under a custom
  “Educational Use License” that is non-commercial only and restricts
  redistribution and mirroring, so its build is not published here.

Every other folder in the archive is represented.

### Built from source, or binary only

**122 entries are compiled from source here.** The other 35 ship a binary, and
each card says which:

- **29 are marked `binary only`** — the archive's `games_precompiled/` and
  `tools_precompiled/` categories. No source for these survives anywhere; the
  archive recovered a compiled `.HEX` and nothing else, so they cannot be
  rebuilt. The **Binary only** tab on the page filters to exactly these.
- **6 are marked `prebuilt hex`** — source exists, but the author's own
  binary is what runs here (see below).

Most of the binary-only titles were recovered by decoding the `.HEX` files in a
fan-made SD-card compilation back to raw binary and reading the plaintext
strings Gamebuino sketches leave in flash — title screens, credits, "Game
Over" text — to identify what each one actually was.

Each entry was compiled with the Arduino IDE 1.8.19 AVR toolchain (avr-gcc 7.3)
for `arduino:avr:uno` — the ATmega328 at 16 MHz — against Gamebuino Classic
library 0.5.2.

Six entries ship as a prebuilt `.hex` from their own author and are marked
`prebuilt hex` on the page. **DarkTower**, **DeathMaze**,
**Gamebuino-SuperSpaceShooter** and **MAKERbuino-Etch-A-Sketch** sit in a
source-bearing folder but kept only their build.
**B-Rally** ships a Simbuino-specific build alongside its normal one, which is
the one that runs here. **sokobuino** does rebuild cleanly, but the resulting
binary misbehaves: `current_gui_state` ends up holding 4, which matches no
branch in its `loop()`, so it draws nothing and its level index lands at 1028
in a 600-level set. The author's own `.hex` runs correctly, so that ships
instead.

### The fixes that were needed

Nothing under the source archive was modified. The build stages a copy of each
game folder and patches the copy. Every patch is a small, commented script in
[`build/fixups/`](build/fixups/), one per game, applied at build time; the three
libraries that had to be recovered are in [`build/libs/`](build/libs/). The
fixes fall into a handful of categories:

- **Stray non-breaking spaces** — sketches pasted out of a web forum carry
  U+00A0 where a plain space belongs. Handled generically, decoding the file
  first so that a French `à` (`C3 A0`) does not lose its second byte.
- **`PROGMEM` data that must now be `const`** — avr-gcc has required this since
  4.6. Adding `const` means propagating it through the pointers and function
  signatures that touch the data, rather than casting it away or dropping
  `PROGMEM` (which would move kilobytes of tables into 2 KB of RAM).
- **Removed types and renamed APIs** — `prog_uchar` no longer exists;
  `gb.begin(title)` split into `begin()` + `titleScreen()`; `setCursor(x, y)`
  became `cursorX`/`cursorY`; `setTextSize()` became `fontSize`. All documented
  in the library's own `changelog.md`.
- **Two programs in one sketch folder** — the Arduino builder concatenates every
  `.ino` in a folder, so a repo holding both a Polish and an English build, or a
  starter and its answer key, defines `loop()` twice. The redundant one is
  dropped from the staged copy.
- **Missing third-party libraries** — `petit_fatfs` was recovered from the
  Gamebuino library's own git history (a 2016 commit removed it);
  `LinkedList` and `GB_Fat` from their original upstream repositories.
- **Sound channels** — see below.

### Sound: NUM_CHANNELS

The library is configured by editing `utility/settings.c`, and the era's
workflow was to copy a game's own `settings.c` over the library's before
building. `NUM_CHANNELS` defaults to **1**, and `Sound::playTrack` /
`playPattern` simply `return` when handed a channel `>= NUM_CHANNELS`. A game
whose music plays on channel 1 or 2 therefore compiles and runs perfectly and
is **silent**, while its channel-0 sound effects still play — which is exactly
what a stock build sounds like.

Four games are affected, found by [`build/chanscan.py`](build/chanscan.py):
101 Starships and Super Crate Buino (3 channels), MasterKebab and Community RPG
(2). 101 Starships ships its own `settings.c`, so that one is used — but only
the block it labels *"SETTINGS YOU CAN EDIT"*. Its *"leave alone"* constants
belong to the older library it was written against: it sets
`VOLUME_GLOBAL_MAX 1`, while 0.5.2 scales output by `<< globalVolume) / 128`
and falls back to `globalVolume = VOLUME_GLOBAL_MAX` when no settings page is
present — carrying that value over quantises every sample to zero.

Verified by instrumenting `OCR2B`, the PWM register the library drives and the
emulator listens on. 101 Starships now matches the author's own released
`101STAR.HEX` almost exactly (≈2,400 register writes per 2 s of play against
his ≈2,450, 117 distinct output levels against 118), where the stock 1-channel
build managed a couple of hundred. The other three all gained sustained audio
against a 1-channel control of the same sketch.

### Known limitations

**LunarRun** compiles cleanly but renders nothing under this emulator — three
lit pixels and no more. The author's own `LUNARRUN.HEX`, which the archive also
ships, behaves identically, so this is not the rebuild: it is the emulator or
the game itself. It is the one entry with no preview image.

**cruiser** — a portal-based 3D engine — renders correctly, but firing a shot
with **A** crashes it. It dereferences a wild pointer while doing so
(`X = 0x9306`, past the 0x900 end of RAM, inside `loop_through_segment_walls`).
Real hardware tolerates that read; both this emulator and the standalone
Simbuino index an array and fault. It is the game's own bug, not a build or
emulator problem, and its screenshot is therefore taken without pressing A.

### The SD card

Five entries read data files off the card, so the player mounts a shared
FAT16 image, [`webemulator/sdcard.img`](webemulator/sdcard.img), for them.
It is built by [`build/mksd.py`](build/mksd.py) and holds:

| File | Used by | Source |
|---|---|---|
| `B-RALLY.DAT` | B-Rally | the card image the author shipped |
| `DATA.DAT`, `SOUND.DAT` | Community RPG | `games/gamebuino-community-rpg/src/` |
| `SDMAP.DAT` | sd_map_test | `tools/sd_map_test/` |
| `WOLF3D.DAT` | Wolfenduino | `games/Wolfenduino/` — its compressed level data |
| `DF01.LDV` | Gamebookuino | `games/Gamebookuino/books+LDV/` — the book itself |
| `THORDAR.DAT` | Thordar's Adventure | `games_precompiled/ThordarsAdventure/` |

Without their data these say so plainly rather than failing quietly:
Wolfenduino draws "SD CARD MOUNT ERROR", Gamebookuino stops at its title
screen.

Two further binaries name a data file in their own embedded strings but never
issue a single SD command in the emulator, so their data is **not** bundled:
`OperationFox` (`EP1.DAT`, 4.8 MB) and `PlayBuino` (`MEDIA.WAV`, 3.2 MB). Both
were tested with a card image built for them and neither touched it — adding
8 MB to this repository on that basis would have been guesswork.

The base image was a "superfloppy" — `mkfs.fat` straight onto the device, no
partition table. Petit FatFs (B-Rally) accepts that, but GB_Fat (Community RPG)
reads sector 0 and rejects any card whose partition-1 type byte is not a FAT16
one, which is why that game reported *"SD card not found."* The image is now
wrapped in a real MBR; every reader involved accepts a partitioned card, and
only GB_Fat requires it. It is trimmed of trailing empty space, hence the
`SdDevice.js` change noted above.

`sd_map_test` gets the card mounted but still cannot read it: it uses SdFat,
whose card-init handshake needs commands (`CMD9`/`CMD10` and friends) that
Simbuino's deliberately minimal SD device does not answer, so it spins on
`CMD0` and never mounts. Same for `chip-8-gamebuino`, which additionally uses
the card as writable swap space — the emulated card is read-only.

Two other entries look like SD users but are not: `Pirates` has its SD check
short-circuited by the author with an explicit *"ONLY for simbuino test"*
early return, and the SD code in the `CopterStrike` repository belongs to its
separate mission-loader sketch, not to the game that is built here.
[`build/sdscan.py`](build/sdscan.py) re-derives all of this from the sources.

`Radio` wants an `EVENTS.DAT` that the repository does not ship, and is a
front-end for an RDA5807 FM tuner chip that the emulator does not emulate at
all, so it cannot do anything useful here either way.

### Reproducing the build

From [`build/`](build/), with the Arduino IDE at `C:\arduino` and the source
archive at `C:\github\gamebuino_classic_source_codes`:

```
python discover.py      # find every sketch in the archive
python select.py        # pick the primary sketch per folder
python chanscan.py      # which sketches need more than one sound channel
python build.py         # compile all 120 targets (8 in parallel)
python meta.py          # join build results with the archive's README metadata
python mksd.py          # build the shared SD card image
python gen_index.py     # write index.html

node serve.js .. 8123   # then, for screenshots:
node shots.js --force
```

## Screenshots

Captured by running each build in the emulator under headless Chrome (Puppeteer,
on the Node that ships with the Emscripten SDK). Each game runs past the
library's boot splash, then A is pressed up to three times with the emulator
running in between, and the frame with the most detail is kept — which is why
some cards show a title screen and others show gameplay. The images are the raw
84×48 framebuffer scaled 4× with nearest-neighbour.

## Publishing to GitHub Pages

Serve the repository root. GitHub Pages picks its entry file in the order
`index.html` → `index.md` → `README.md`, so [`index.html`](index.html) is the
site and this README stays what it is: the repo's front page on github.com.

Two things this repo depends on:

- **`.nojekyll`** is present, so Pages serves the files verbatim instead of
  running them through Jekyll. Nothing here needs Jekyll, and a Jekyll build
  would silently drop any path beginning with `_`.
- **Nothing is tracked in Git LFS.** Pages serves an LFS-tracked file as its
  pointer text, not its contents, which would break every `.hex` and every
  screenshot. Nothing here is big enough to need LFS — the largest file is the
  1.5 MB SD card image — so all links stay plain relative paths.

## Downloading a game

Every card has a **.hex** button next to Play. That is the file a real
Gamebuino Classic wants: copy it to the root of a FAT-formatted SD card and
pick it from the console's loader.

The console's loader reads DOS 8.3 short filenames off the card, so a download
is offered under one â€” "Worlds Hardest Game" saves as `WORLDSHA.HEX`,
"Gamebuino Catcher" as `CATCHER.HEX` â€” while the copy in this repository keeps
its descriptive name. The short names are derived from the titles, with the
redundant `GAMEBUINO` prefix dropped, and are unique across the collection.

## Source links on each card

Two different links can appear on a card, and which one shows is derived from
how the archive actually stores that entry (its `.gitmodules`, cross-checked
against git's own index):

- **Original repo** â€” the upstream repository, for the 98 entries the archive
  keeps as a **git submodule**.
- **Archived source** â€” the folder in the archive, for the 21 entries whose
  files are **really committed there**: things recovered from a forum post, a
  Mediafire link or a personal site, where the archive is the only place the
  code still exists.

A submodule folder is only a commit pointer, so browsing it shows a reference
rather than the game's source â€” linking to it as "archived source" would be a
dead end, so those cards link upstream instead. One entry (BigBlackBox) shows
both: its files are committed here *and* it has a live mirror repository.

## Credits

- **Simbuino / Simbuino4Web** — Mark Feldman ("Myndale"), MIT.
  See [`webemulator/SIMBUINO-LICENSE.txt`](webemulator/SIMBUINO-LICENSE.txt).
- **Gamebuino Classic** and its library — Aurélien Rodot and contributors, LGPLv3.
- **Every game and tool** — its own author, under its own licence. Several have
  **no licence specified at all** by their original author; that is noted on the
  page rather than assumed permissive.
