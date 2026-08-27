/*
 * gamebuino_main_alt.h -- RECONSTRUCTION, not the original file.
 *
 * angyongen's MAKERbuino tools (makerbuino-frequency-generator,
 * makerbuino-sd-explorer, makerbuino-midi) include this header instead of
 * <Gamebuino.h>.  It is the entry point of what his makerbuino-midi README
 * calls "my modified gamebuino library".  That library was never published:
 * it is absent from every one of his GitHub repositories (including his
 * Gamebuino-Classic fork, which is stock 0.5.2 plus one unrelated commit) and
 * from the whole gamebuino_classic_source_codes archive.
 *
 * makerbuino-sd-explorer.ino switched from
 *     #include <Gamebuino.h>
 * to
 *     #define DISPLAYDIRECT
 *     #include <gamebuino_main_alt.h>
 * in commit f4584ac (2019-08-24) "added support for direct display mode
 * ( no screen buffer ) to free SRAM", so the original header wrapped a
 * Gamebuino core that could draw straight to the LCD instead of through the
 * 504-byte frame buffer.
 *
 * Every *symbol* the three sketches use out of this header -- Gamebuino,
 * gb.begin/update/setFrameRate, gb.display (print/println/clear/persistence/
 * textWrap/fontSize/fontWidth/fontHeight/cursorX/cursorY/update),
 * gb.buttons.pressed/repeat/update, gb.battery.thresholds, BTN_*, SD_CS --
 * is stock Gamebuino Classic 0.5.2.  So this shim forwards to the stock
 * library, which reproduces the sketches' behaviour exactly as it was before
 * that 2019 commit.
 *
 * DISPLAYDIRECT is a configuration macro of the missing library rather than a
 * symbol the sketches call, and it cannot be honoured here: the stock Display
 * class always renders into its frame buffer.  The sketch-side effects of the
 * macro (fewer rows per page, menu animation disabled) still apply because
 * those #ifdefs live in the sketch.  The only lost behaviour is the RAM saving
 * and the unbuffered drawing; the buffered path draws the same pixels.
 */
#ifndef GAMEBUINO_MAIN_ALT_H
#define GAMEBUINO_MAIN_ALT_H

#include <Gamebuino.h>

#endif /* GAMEBUINO_MAIN_ALT_H */
