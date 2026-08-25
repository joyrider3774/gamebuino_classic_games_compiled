# Upstream emulator sources

Byte-exact copies of the Simbuino4Web files that [`../js/`](../js/) ships in
modified form, kept here so every change to the emulator is visible and
reproducible.

**Upstream:** [Myndale/Simbuino](https://github.com/Myndale/Simbuino),
commit `6800990c07fdd745248f1b171dfe692366083cc5` (2022-06-23),
`src/Simbuino4Web/Simbuino4Web/Scripts/Views/`.

Every other file in [`../js/`](../js/) is upstream's, unmodified.

[`simbuino4web.patch`](simbuino4web.patch) is the complete diff. It was
generated ignoring line endings, because upstream ships a mix of CRLF and LF
and only the substance matters:

```
diff -u --strip-trailing-cr upstream/<file> ../js/<file>
```

## The four fixes

### `AtmelContext.js` — undefined `SREG`

`UpdateInterruptFlags()` tested a bare `SREG`, which does not exist in the
JavaScript port (every other line writes `AtmelContext.SREG`). It threw a
`ReferenceError` straight out of the emulator's frame loop, freezing any sketch
that reached that path — sokobuino's own released `.hex` stalls on frame 1
without this fix.

Only the name is qualified. The `== 0` comparison is left exactly as upstream
wrote it, so interrupt behaviour is unchanged. The C# core has the identical
comparison — see below.

### `AtmelProcessor.js` — `ASR` stores an unmasked negative value

`ASR` sign-extends `Rd` before shifting, so the result is negative whenever
`Rd >= 128`. `AtmelContext.R` is a plain JavaScript array, so storing that
result unmasked leaves a negative number in the register file — which then
poisons the `FlagsAdd[]`/`FlagsSub[]` lookups, since those tables are indexed
by register values. The C# core masks the store (`R & 0xff`).

`>> 4` on a signed int compiles straight to `ASR`, so this hit fixed-point code
hardest: it is what kept **cruiser** stuck in an unbounded line-drawing loop,
never completing a frame.

### `AtmelProcessor.js` — `MULSU` sign extension

`MULSU` multiplies a **signed** `Rd` by an **unsigned** `Rr`. The port
sign-extended both operands, so the product was wrong whenever `Rr >= 128`.
avr-gcc emits `MULSU` inside its 16×16 signed multiply helpers, so this
affected any sketch doing fixed-point arithmetic.

### `SdDevice.js` — reads past the end of a card image

Indexing past the end of a `Uint8Array` yields `undefined` rather than
throwing, so upstream's `catch` never fired and `undefined` was clocked out
over SPI a byte at a time. Returning `0` instead lets a card image be stored
trimmed of its trailing empty space (16 MB → 1.5 MB here).

## Where these came from

Simbuino ships **two** emulators, and they do not share code: a C# desktop
application (`src/Simbuino.Emulator/`) and this JavaScript port
(`src/Simbuino4Web/`), whose files map onto each other one-for-one. The port
can drift from the C# core, and has.

All three CPU-core fixes above make the JavaScript behave the way the C#
already does:

| | C# core | JavaScript port |
|---|---|---|
| `SREG` in `UpdateInterruptFlags` | `SREG.I == 0` — a resolvable static field | bare `SREG` — undefined |
| `MULSU` operands | `(sbyte)Rd * (byte)Rr` | both sign-extended |
| `ASR` result store | `R & 0xff` | stored unmasked, so negative |

Comparing the two CPU cores in full turned up nothing else worth porting:

- **Opcode coverage is equivalent.** The port groups instructions differently
  (`LD_X`/`LD_Y`/`LD_Z`, `BCLR`/`BSET` covering the `CLx`/`SEx` aliases) but
  covers the same patterns, including the `10q0qq` displacement forms.
- **The same 14 instructions are stubbed in both** — `BREAK`, `DES`, `EICALL`,
  `EIJMP`, `ELPM1`–`3`, `FMUL`, `FMULS`, `LAC`, `LAS`, `LAT`, `SLEEP`, `WDR`.
  None are reachable from ATmega328 Arduino code.
- **`MULSU` was the only operand-signedness divergence** (`MUL` and `MULS`
  agree).
- **`ASR` was the only unmasked register store that matters.** The port also
  omits the mask on `AND`, `ANDI`, `EOR`, `OR`, `ORI`, `LSR` and `ROR`, but
  those results are inherently 0–255, so only `ASR` can leave a negative value
  behind.
- **Status flags agree.** The port precomputes `FlagsAdd[]`/`FlagsSub[]` lookup
  tables that the C# does not have, which makes the arithmetic instructions
  look at a glance as though they skip flag updates.
- **SD card command coverage is identical** — both handle only CMD0, CMD8,
  CMD16, CMD17, CMD23, CMD55, CMD58 and ACMD41. Neither implements CMD24
  (write) or CMD9/CMD10, which is why the SdFat-based sketches here cannot
  mount the card on either emulator.

## Ported from the standalone: the grey blend

This one is an addition, not a bug fix. `LcdDevice.cs` has an optional
**Persistence** mode that simulates the LCD's response time: it integrates each
pixel's state over the elapsed clock cycles, averages that against the previous
frame, and buckets the result into three levels — `0`, `128`, `255`. Its own
options dialog calls it "more suitable for games that employ double-buffered
grayscale".

The library draws `GRAY` as a checkerboard that inverts every frame —
`Display.cpp` computes `g = y ^ frameCount` and lights a pixel when
`(x ^ g) & 1` — so it is spatial *and* temporal dithering. On a one-bit panel
that only resolves into a mid-tone once the response time is simulated;
otherwise it shimmers in the player, and a screenshot catches whichever phase
the frame happened to hold. 15 entries use `GRAY`.

`Lcd.js` had no equivalent — it copied pixel state straight to the canvas. The
algorithm is ported verbatim, along with the three-level rendering it needs
(the mid-tone is the midpoint of the foreground and the current backlight
colour). `player.js` turns it **on** by default and offers a *Grey blend*
toggle; upstream's standalone defaults it off. `?gray=0` disables it for a
single link, and the choice is remembered per browser.
