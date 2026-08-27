# makerbuino-sd-explorer (angyongen) -- staging fix-up.
#
# Two things the published repository never contained:
#
#   gbTools.h   The sketch does #include "gbTools.h" //pause and waitForUpdate.
#               The repo carries the same code twice under other names --
#               gbTools.ino (commit 27bff7b, later deleted) and x/gbTools.cpp,
#               which is a full header-guarded file that Arduino never compiles
#               because it sits in a subfolder.  x/gbTools.cpp is reproduced
#               verbatim below; only pause_ABC_UDLR (used once, when the card
#               fails to initialise) has no surviving original and is written
#               here to match pause().
#
#   SdFat v1    The sketch is from 2019 and uses the SdFat 1.x API: dir_t,
#               ldir_t, DIR_ATT_*, FatFile::openRoot(SdFat*), SdFat::vwd(),
#               SPI_HALF_SPEED, FreeStack.h.  The only SdFat installed here is
#               the Adafruit fork of SdFat 2.3.x, where none of that exists.
#               A copy of upstream greiman/SdFat 1.1.4 is dropped into the
#               staged game's own libraries/ folder, which build.py puts ahead
#               of the sketchbook on -libraries, so no other target's SdFat
#               resolution changes.
import os
import shutil

GBTOOLS_H = '''
#ifndef GAMEBUINO_TOOLS
#define GAMEBUINO_TOOLS

#include <Gamebuino.h>

void waitForUpdate(Gamebuino &gb)
{
  while (!gb.update()) {}
}

void pause(Gamebuino &gb) {
    gb.display.persistence = true;
    while(true)
    {
      if(gb.update())
      {
        if(gb.buttons.pressed(BTN_A)){break;}
        if(gb.buttons.pressed(BTN_B)){break;}
        if(gb.buttons.pressed(BTN_C)){break;}
      }
    }
}

void pause_ABC_UDLR(Gamebuino &gb) {
    gb.display.persistence = true;
    while(true)
    {
      if(gb.update())
      {
        if(gb.buttons.pressed(BTN_A)){break;}
        if(gb.buttons.pressed(BTN_B)){break;}
        if(gb.buttons.pressed(BTN_C)){break;}
        if(gb.buttons.pressed(BTN_UP)){break;}
        if(gb.buttons.pressed(BTN_DOWN)){break;}
        if(gb.buttons.pressed(BTN_LEFT)){break;}
        if(gb.buttons.pressed(BTN_RIGHT)){break;}
      }
    }
}
#endif /* GAMEBUINO_TOOLS */
'''


def write_if_changed(path, text):
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            if f.read() == text:
                return
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


write_if_changed(os.path.join(SKETCH_DIR, 'gbTools.h'), GBTOOLS_H)

def install(vendor_name, lib_name):
    src = os.path.join(BUILD, 'vendor', vendor_name)
    dst = os.path.join(GAME_ROOT, 'libraries', lib_name)
    if not os.path.isdir(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copytree(src, dst)


install('SdFat', 'SdFat')

# The sketch #defines DISPLAYDIRECT before including gamebuino_main_alt.h and
# does not fit in the ATmega328's 2 KB with the stock 504-byte frame buffer
# (sd0 and sd1 are 596 bytes each on their own -- the link fails by 60 bytes).
# vendor/Gamebuino_Classic_direct is Gamebuino Classic 0.5.2 with the
# unbuffered "direct display" mode of angyongen's unpublished library
# reinstated; see the note at the top of its utility/Display.cpp.  It goes into
# the staged game's own libraries/, which build.py passes ahead of the
# sketchbook, so no other target sees it.
install('Gamebuino_Classic_direct', 'Gamebuino_Classic')
