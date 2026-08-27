r"""avr-gcc requires PROGMEM data to be const.

Its tables are read back only through pgm_read_*, so const keeps them in flash
rather than moving them into the 2 KB of RAM.
"""
progmem_const(SKETCH_DIR)
