r"""sokobuino targets the pre-0.4 Gamebuino library API.

Four things changed in Gamebuino_Classic before 0.5.2 (see the library's
changelog.md):

1. Buttons.h / Display.h / Sound.h / Battery.h / Backlight.h moved out of the
   library root into utility/ and are now pulled in by Gamebuino.h itself, so
   the standalone <Buttons.h> etc. includes no longer resolve.
2. "gb.titleScreen() function added. It's used to display the main menu instead
   of gb.begin() ... It should be called just after gb.begin() with the
   arguments you were used to put in the gb.begin() function."
3. "gb.display.setCursor(x,y) is now gb.display.cursorX and gb.display.cursorY".
4. avr-gcc 7.3 rejects a non-const PROGMEM variable ("must be const in order to
   be put into read-only section"); the 2012 toolchain allowed it.

All four are mechanical source-compatibility edits, no behaviour change.
"""
import os, re

MAIN_INO = os.path.join(SKETCH_DIR, os.path.splitext(MAIN)[0] + '.ino')
with open(MAIN_INO, encoding='utf-8', errors='surrogateescape') as f:
    txt = f.read()

# (1) headers that Gamebuino.h now provides
txt = re.sub(
    r'^([ \t]*)#\s*include\s*[<"](Buttons\.h|Display\.h|Sound\.h|Battery\.h|Backlight\.h)[>"]',
    r'\1// #include <\2>  // now in utility/, included by Gamebuino.h',
    txt, flags=re.MULTILINE)

# (2) gb.begin(F("...")) -> gb.begin(); gb.titleScreen(F("..."));
txt = re.sub(r'\bgb\.begin\(\s*(F\(.*?\))\s*\)\s*;',
             r'gb.begin();\n  gb.titleScreen(\1);', txt)

# (3) gb.display.setCursor(x, y) -> assignment to the cursorX/cursorY members.
# Scanned by hand rather than by regex because several call sites nest
# parentheses in their arguments, e.g. setCursor(60 - (pos * 4), 14).
CALL = 'gb.display.setCursor('
while True:
    i = txt.find(CALL)
    if i < 0:
        break
    j = i + len(CALL)
    depth, comma = 1, -1
    while depth:
        ch = txt[j]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ',' and depth == 1:
            comma = j
        j += 1
    x = txt[i + len(CALL):comma].strip()
    y = txt[comma + 1:j - 1].strip()
    txt = (txt[:i]
           + '(gb.display.cursorX = (%s), gb.display.cursorY = (%s))' % (x, y)
           + txt[j:])

# (4) "PROGMEM uint16_t name[] = ..." -> "const uint16_t name[] PROGMEM = ..."
txt = re.sub(r'^PROGMEM\s+(\w+)\s+(\w+)\[\]\s*=',
             r'const \1 \2[] PROGMEM =', txt, flags=re.MULTILINE)

with open(MAIN_INO, 'w', encoding='utf-8', errors='surrogateescape') as f:
    f.write(txt)
