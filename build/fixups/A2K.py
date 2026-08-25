"""A2K was written against Gamebuino library 0.3.x, whose Buttons.h / Display.h /
Sound.h lived at the top level of the library.  In 0.5.2 they were moved into
Gamebuino_Classic/utility/ and are pulled in by Gamebuino.h itself, so the
standalone <Buttons.h> / <Display.h> / <Sound.h> includes no longer resolve.
Comment them out; Gamebuino.h (still included) provides all three.
"""
import os, re

MOVED = ('Buttons.h', 'Display.h', 'Sound.h', 'Battery.h', 'Backlight.h')

pat = re.compile(
    r'^([ \t]*)#\s*include\s*[<"](' + '|'.join(re.escape(h) for h in MOVED) + r')[>"](.*)$',
    re.MULTILINE)


def _fix(path):
    with open(path, encoding='utf-8', errors='surrogateescape') as f:
        txt = f.read()
    new = pat.sub(lambda m: '%s// #include <%s>%s  // moved to utility/ in '
                            'Gamebuino_Classic 0.5.2, included by Gamebuino.h'
                            % (m.group(1), m.group(2), m.group(3)), txt)
    if new != txt:
        with open(path, 'w', encoding='utf-8', errors='surrogateescape') as f:
            f.write(new)


for dirpath, _d, files in os.walk(SKETCH_DIR):
    for fn in files:
        if fn.lower().endswith(('.ino', '.pde', '.h', '.hpp', '.c', '.cpp')):
            _fix(os.path.join(dirpath, fn))
