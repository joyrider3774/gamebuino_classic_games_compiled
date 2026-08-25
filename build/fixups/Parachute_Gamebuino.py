"""Parachute_Gamebuino -- source-encoding repair.

The upstream .ino is UTF-8 with a BOM and contains French accented letters
(a-grave / e-acute / e-grave) plus typographic quotes.  Two problems:

  1. The harness' generic non-breaking-space pass rewrites every bare 0xA0
     byte to a space.  In this file the only 0xA0 bytes are the trailing
     byte of the UTF-8 sequence for 'a-grave' (C3 A0), so that pass turns
     valid 'a-grave' into a dangling C3 followed by a space.  Undo that
     first, then transliterate the whole file to plain ASCII so no stray
     high byte can reach the preprocessor at all.

  2. Line 295 reads

         else gb.display.drawBitmap(16 , 1<e-acute>, Para_5) ;

     i.e. the Y coordinate literal is "1" followed by a corrupted
     non-digit character.  See the comment on PARA_CASE6_Y below.
"""
import io
import os
import re

TARGET = 'Parachute_v0_3.ino'

# --- the coordinate substitution -------------------------------------------
# Dessine_Para() case 6 draws the Para_5 sprite for lane 1 and lane 3 (the
# lane-2 sub-case is handled on the line immediately above).  Its Y literal
# is the corrupted one.  Every other Para_5 draw around it pins the value:
#
#     case 5:  drawBitmap(62 - 16*ColX, 12 + (3 - ColX)*3, Para_5)
#     case 6:  if (ColX==2) drawBitmap(29, 17, Para_5)
#              else         drawBitmap(16, 1?, Para_5)      <-- corrupted
#     case 7:  drawBitmap(13, 17, Para_5)
#
# The neighbouring lane-2 branch of the *same* case uses 17 and the *next*
# stage of the fall uses a fixed 17 for every lane, so the paratrooper is
# already at its final resting height by case 6.  17 is the only reading
# that keeps the fall monotonic for every lane (lane 3: 12 -> 17 -> 17;
# lane 1: 18 -> 17 -> 17).
PARA_CASE6_Y = '17'

# --- accented characters -> ASCII ------------------------------------------
TRANSLIT = {
    'é': 'e',   # e-acute
    'è': 'e',   # e-grave
    'ê': 'e',   # e-circumflex
    'à': 'a',   # a-grave
    'â': 'a',   # a-circumflex
    'ç': 'c',   # c-cedilla
    'î': 'i',   # i-circumflex
    'ô': 'o',   # o-circumflex
    'ù': 'u',   # u-grave
    'û': 'u',   # u-circumflex
    '“': '"', '”': '"',
    '‘': "'", '’': "'",
    '–': '-', '—': '-',
    '°': ' ',
    ' ': ' ',
}

path = os.path.join(SKETCH_DIR, TARGET)
raw = open(path, 'rb').read()

# undo the generic NBSP pass' damage to 'a-grave' (C3 A0 -> C3 20)
raw = raw.replace(b'\xc3\x20', b'\xc3\xa0')

text = raw.decode('utf-8-sig', errors='strict')

# fix the corrupted Y coordinate before the blanket transliteration, so the
# e-acute in it can never silently turn into "1e".
text, n = re.subn(
    r'(drawBitmap\(\s*16\s*,\s*)1[^\x00-\x7f](\s*,\s*Para_5\s*\))',
    r'\g<1>' + PARA_CASE6_Y + r'\g<2>',
    text)
if n == 0 and ('drawBitmap(16 , %s, Para_5)' % PARA_CASE6_Y) not in text:
    raise RuntimeError('Parachute: case-6 Y coordinate not found (n=%d)' % n)

for bad, good in TRANSLIT.items():
    text = text.replace(bad, good)

# anything still non-ASCII would be a surprise -- fail loudly rather than
# emit a file the compiler will choke on.
leftover = sorted({c for c in text if ord(c) > 127})
if leftover:
    raise RuntimeError('Parachute: un-transliterated characters %r' % leftover)

with io.open(path, 'w', encoding='ascii', newline='') as f:
    f.write(text)
