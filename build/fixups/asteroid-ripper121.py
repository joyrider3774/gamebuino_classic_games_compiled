"""asteroid-ripper121 -- port from the pre-June-2014 Gamebuino API.

This sketch predates three documented breaking changes in the Gamebuino
library (see changelog.md in Gamebuino_Classic):

  2014-06-09  every PROGMEM variable must now be `const` (an avr-gcc
              requirement, not a library one -- avr-gcc > 4.6 refuses to
              put a non-const object in .progmem).
  2014-06-09  gb.begin(name, logo) split into gb.begin() plus
              gb.titleScreen(name, logo).
  2014-06-24  "useless setters replaced by public variables":
                setCursor(x, y) -> cursorX / cursorY
                setTextSize(s)  -> fontSize

Vendoring the old library instead is not an option: the pre-2014-06-13
releases themselves do not compile with a modern avr-gcc (they still use
prog_char and non-const PROGMEM), which is exactly what the 2014-06-13
changelog entry is about.  So the sketch is translated forward, following
the changelog's own migration notes.

The one judgement call is setTextSize(0).  The old Display::setTextSize
came straight from Adafruit-GFX, which clamps: `textsize = (s > 0) ? s : 1`
-- so 0 meant "normal size".  Classic 0.5.2's fontSize is used raw
(drawChar(..., fontSize) and cursorX += fontSize * fontWidth), so a literal
0 would draw nothing and never advance the cursor.  It is therefore mapped
to 1, which is what the sketch actually rendered at.
"""
import io
import os
import re

TARGET = 'asteroid.ino'

path = os.path.join(SKETCH_DIR, TARGET)
with io.open(path, encoding='utf-8', errors='replace', newline='') as f:
    text = f.read()
original = text

# 1. PROGMEM arrays need const (idempotent: skip ones already const)
text = re.sub(r'\bstatic\s+(?!const\b)unsigned\s+char\s+PROGMEM\b',
              'static const unsigned char PROGMEM', text)

# 2. gb.begin(name, logo)  ->  gb.begin(); gb.titleScreen(name, logo);
text = re.sub(r'\bgb\.begin\(\s*(F\(.*?\))\s*,\s*([A-Za-z_]\w*)\s*\);',
              r'gb.begin();\n  gb.titleScreen(\1, \2);', text)

# 3. setTextSize(s) -> fontSize = s   (0 meant "normal" in the old library)
def _textsize(m):
    val = m.group(1).strip()
    return 'gb.display.fontSize = %s;' % ('1' if val == '0' else val)
text = re.sub(r'\bgb\.display\.setTextSize\(\s*([^()]*?)\s*\);', _textsize, text)

# 4. setCursor(x, y) -> cursorX / cursorY
text = re.sub(r'\bgb\.display\.setCursor\(\s*([^,()]+?)\s*,\s*([^,()]+?)\s*\);',
              r'gb.display.cursorX = \1; gb.display.cursorY = \2;', text)

for leftover in ('setCursor', 'setTextSize', 'setTextWrap'):
    if leftover in text:
        raise RuntimeError('asteroid: %s still present after port' % leftover)

if text != original:
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
