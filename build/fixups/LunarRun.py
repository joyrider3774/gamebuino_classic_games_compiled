r"""avr-gcc requires PROGMEM data to be const.

LunarRun's ship sprite table (`ship_sprite_data angles[] PROGMEM`) is only ever
read back through pgm_read_*, so const keeps it in flash instead of moving it
into the 2 KB of RAM.
"""
progmem_const(SKETCH_DIR)
