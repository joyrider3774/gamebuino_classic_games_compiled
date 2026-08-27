# makerbuino-midi (angyongen) -- staging fix-up.
#
# Two libraries have to be target-local rather than global:
#
#   SdFat v1    The sketch uses the SdFat 1.x API (SdFat::vwd(), FatFile::
#               openNext/getSFN, SPI_HALF_SPEED) and its README names
#               greiman/SdFat.  Only the Adafruit fork of SdFat 2.3.x is
#               installed in the sketchbook, where none of that exists.  A copy
#               of upstream SdFat 1.1.4 goes into the staged game's own
#               libraries/ folder, which build.py puts ahead of the sketchbook
#               on -libraries, so no other target's SdFat resolution changes.
#
#   Gamebuino   The sketch produces sound with angyongen's Sound4 library,
#               whose ISR(TIMER1_COMPA_vect) is the same vector as the one in
#               Gamebuino Classic's utility/Sound.cpp -- linking both is a
#               duplicate __vector_11.  His unpublished "modified gamebuino
#               library" evidently did not carry the stock sound engine.
#               vendor/Gamebuino_Classic_nosound is Gamebuino Classic 0.5.2
#               with NUM_CHANNELS set to 0 in utility/settings.c, which is the
#               library's own documented way (the setting is "between 0 and 4")
#               of compiling out both that ISR and the timer-1 setup in
#               Sound::begin, leaving timer 1 and the audio pin to Sound4.
#               Simply deleting the ISR would have been worse than useless:
#               Sound::begin enables OCIE1A, and an enabled interrupt with no
#               handler resets the board.
import os
import shutil


def install(vendor_name, lib_name):
    src = os.path.join(BUILD, 'vendor', vendor_name)
    dst = os.path.join(GAME_ROOT, 'libraries', lib_name)
    if not os.path.isdir(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copytree(src, dst)


install('SdFat', 'SdFat')
install('Gamebuino_Classic_nosound', 'Gamebuino_Classic')
