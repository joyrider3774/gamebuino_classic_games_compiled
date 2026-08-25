# Blob-Attack: avr-gcc 7.3 requires PROGMEM data to be const.
# All bitmaps in blob_bitmaps.h / menu_bitmap.h are read-only sprite data,
# handed to gb.display.drawBitmap(const uint8_t*), so const propagates cleanly.
# blobs_bitmap[] is a RAM lookup table of pointers into those bitmaps and has
# to become an array of pointers-to-const.
import os, re, io

DECL = re.compile(
    r'(?m)^(?P<i>[ \t]*)(?P<d>(?:byte|char|unsigned\s+char|uint8_t|int|'
    r'unsigned\s+int|uint16_t|long)\b(?:\s+PROGMEM)?\s+[A-Za-z_]\w*\s*\[[^\]]*\]'
    r'(?:\s+PROGMEM)?\s*=)')

def constify(path):
    s = io.open(path, encoding='utf-8', errors='replace').read()
    out = []
    for line in s.splitlines(True):
        if 'PROGMEM' in line and not re.match(r'\s*const\b', line):
            m = DECL.match(line)
            if m:
                line = line[:m.start('d')] + 'const ' + line[m.start('d'):]
        out.append(line)
    new = ''.join(out)
    if new != s:
        io.open(path, 'w', encoding='utf-8', newline='').write(new)

for fn in ('blob_bitmaps.h', 'menu_bitmap.h'):
    fp = os.path.join(SKETCH_DIR, fn)
    if os.path.isfile(fp):
        constify(fp)

# table of pointers into the now-const bitmaps
bp = os.path.join(SKETCH_DIR, 'blob_bitmaps.h')
s = io.open(bp, encoding='utf-8', errors='replace').read()
new = re.sub(r'(?m)^(\s*)byte(\s*\*\s*blobs_bitmap\s*\[)', r'\1const byte\2', s)
if new != s:
    io.open(bp, 'w', encoding='utf-8', newline='').write(new)
