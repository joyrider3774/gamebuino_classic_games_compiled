"""Build the SD card image the web player mounts.

A real Gamebuino kept every game's data on one card, so this does the same:
one FAT16 image holding the data files of every game in the collection that
reads one. It starts from the card image B-Rally shipped with -- known good,
and the reason this format is trusted -- and adds the other games' files.

That image is a "superfloppy": mkfs.fat straight onto the device, with no
partition table. Petit FatFs copes with that, but GB_Fat does not: it reads
sector 0, requires the 0x55AA signature, and rejects the card outright unless
partition 1's type byte is a FAT16 one. So the volume gets wrapped in a real
MBR here. Every reader involved accepts a partitioned card; only GB_Fat
requires it.

Re-running is safe: the image is unwrapped first, so files are replaced rather
than duplicated and the MBR is never applied twice.
"""
import os, sys, struct, datetime

SRC_ROOT = r"C:\github\gamebuino_classic_source_codes"
SITE = os.environ.get("GB_SITE", r"C:\github\gamebuino_classic_games_compiled")
IMAGE = os.path.join(SITE, "webemulator", "sdcard.img")

# 8.3 name on the card  ->  file in the source archive
FILES = {
    # gamebuino-community-rpg: its map/text data and its sound bank
    'DATA.DAT': 'games/gamebuino-community-rpg/src/DATA.DAT',
    'SOUND.DAT': 'games/gamebuino-community-rpg/src/SOUND.DAT',
    # sd_map_test's tilemap
    'SDMAP.DAT': 'tools/sd_map_test/SDMAP.DAT',
    # Wolfenduino streams its compressed level data off the card
    'WOLF3D.DAT': 'games/Wolfenduino/wolf3d.dat',
    # Gamebookuino reads the book itself off the card; the build here is DF01,
    # the French edition of Fighting Fantasy's Warlock of Firetop Mountain
    'DF01.LDV': 'games/Gamebookuino/books+LDV/DF01.LDV',
    # Thordar's Adventure is a binary-only recovery that still shipped
    # its data file alongside the .HEX
    'THORDAR.DAT': 'games_precompiled/ThordarsAdventure/THORDAR.DAT',
    # LittleRacer reads its track geometry off the card
    'CURVES.DAT': 'games_precompiled/LittleRacer/CURVES.DAT',
    'HILLS.DAT': 'games_precompiled/LittleRacer/HILLS.DAT',
    'LANES.DAT': 'games_precompiled/LittleRacer/LANES.DAT',
    'STRAIGHT.DAT': 'games_precompiled/LittleRacer/STRAIGHT.DAT',
    'TRACK.DAT': 'games_precompiled/LittleRacer/TRACK.DAT',
    # Operation Fox's episode data, shipped beside its .HEX; its README says to
    # copy both to the card
    'EP1.DAT': 'games_precompiled/OperationFox/EP1.DAT',
    # PlayBuino plays converted audio from the card; this is the sample its
    # author shipped with the player
    'MEDIA.WAV': 'tools_precompiled/PlayBuino/Gamebuino/MEDIA.WAV',
}

# CHIP-8 programs, kept in the repo rather than in the source archive: they are
# not Gamebuino software, they are what tools/chip-8-gamebuino interprets. The
# sketch offers any root file whose name ends in "8" as a ROM. Provenance and
# authorship: build/chip8roms/README.md.
ROMS = ['BRIX.CH8', 'INVADERS.CH8', 'BLITZ.CH8', 'PONG1.CH8', 'TETRIS.CH8']
ROM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chip8roms')


def make_scale_mid():
    """A minimal Standard MIDI File: one octave up and back, quarter notes.

    makerbuino-midi scans the card root for *.MID and there is no MIDI file
    anywhere in the source archive, so this is written here rather than
    imported from anyone -- it exists purely so the player has something to
    play. Format 0, one track, 96 ticks per quarter note, explicit note-on and
    note-off (no running status), which is the subset the player reads.
    """
    import struct

    notes = [60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67, 65, 64, 62, 60]
    ev = bytearray()
    for n in notes:
        ev += b'\x00' + bytes((0x90, n, 0x50))     # note on,  delta 0
        ev += b'\x60' + bytes((0x80, n, 0x40))     # note off, delta 96
    ev += b'\x00\xff\x2f\x00'                     # end of track

    hdr = b'MThd' + struct.pack('>IHHH', 6, 0, 1, 96)
    trk = b'MTrk' + struct.pack('>I', len(ev)) + bytes(ev)
    return hdr + trk


def make_demo_ch8():
    """A minimal CHIP-8 program: a sprite tracking across the screen.

    chip-8-gamebuino lists the card root and offers any file whose name ends in
    "8" as a ROM. No CHIP-8 program exists in the source archive and the
    circulating classics have murky provenance, so this is written here: it is
    a demo, not one of the well-known games.

    Assembly, loaded at 0x200 as CHIP-8 programs are:

        200  00E0     clear the screen
        202  6000     V0 = 0            x
        204  610C     V1 = 12           y
        206  A220     I  = sprite
        208  D015     draw 5-byte sprite at (V0,V1)   -- XOR, so this shows it
        20A  6208     V2 = 8
        20C  F215     delay timer = V2
        20E  F307     V3 = delay timer
        210  3300     skip the next instruction if V3 == 0
        212  120E     ...otherwise keep waiting
        214  D015     draw again at the same spot     -- XOR, so this erases it
        216  7002     V0 += 2
        218  1208     back to the draw
        220  sprite   a 4x5 open box
    """
    code = bytes([
        0x00, 0xE0,  0x60, 0x00,  0x61, 0x0C,  0xA2, 0x20,
        0xD0, 0x15,  0x62, 0x08,  0xF2, 0x15,  0xF3, 0x07,
        0x33, 0x00,  0x12, 0x0E,  0xD0, 0x15,  0x70, 0x02,
        0x12, 0x08,
    ])
    code += bytes(0x20 - len(code))              # pad up to offset 0x20
    code += bytes([0xF0, 0x90, 0x90, 0x90, 0xF0])  # the sprite
    return code


# files written here rather than taken from the archive, 8.3 name -> builder
GENERATED = {
    'SCALE.MID': make_scale_mid,
    'DEMO.CH8': make_demo_ch8,
}

# a fixed timestamp keeps the image byte-identical across rebuilds
STAMP = datetime.datetime(2016, 1, 1, 0, 0, 0)

PART_LBA = 64          # 4-sector aligned, so clusters stay aligned too
PART_TYPE = 0x06       # FAT16

BOOT_SIG = bytes([0x55, 0xAA])
CHS_USE_LBA = bytes([0xFE, 0xFF, 0xFF])
FAT_PART_TYPES = (0x01, 0x04, 0x06, 0x0B, 0x0C, 0x0E, 0x86)


def unwrap(img):
    """Return the FAT volume inside `img`, whether or not it is partitioned."""
    if img[510:512] == BOOT_SIG and img[450] in FAT_PART_TYPES:
        lba = struct.unpack_from('<I', img, 454)[0]
        return img[lba * 512:], lba
    return img, None


def wrap(volume):
    """Put a single-partition MBR in front of a FAT volume."""
    total = struct.unpack_from('<H', volume, 19)[0] or struct.unpack_from('<I', volume, 32)[0]
    vol = bytearray(volume)
    struct.pack_into('<I', vol, 28, PART_LBA)      # BPB hidden sectors

    mbr = bytearray(512)
    e = 446
    mbr[e] = 0x00                                  # not bootable
    mbr[e + 1:e + 4] = CHS_USE_LBA                 # CHS is meaningless here
    mbr[e + 4] = PART_TYPE
    mbr[e + 5:e + 8] = CHS_USE_LBA
    struct.pack_into('<I', mbr, e + 8, PART_LBA)
    struct.pack_into('<I', mbr, e + 12, total)
    mbr[510:512] = BOOT_SIG

    return bytes(mbr) + bytes((PART_LBA - 1) * 512) + bytes(vol)


class Fat16:
    def __init__(self, data):
        self.d = bytearray(data)
        self.bps = struct.unpack_from('<H', self.d, 11)[0]
        self.spc = self.d[13]
        self.rsvd = struct.unpack_from('<H', self.d, 14)[0]
        self.nfat = self.d[16]
        self.rootent = struct.unpack_from('<H', self.d, 17)[0]
        self.spf = struct.unpack_from('<H', self.d, 22)[0]
        if self.d[510:512] != BOOT_SIG:
            raise ValueError('not a FAT boot sector')
        self.fat0 = self.rsvd * self.bps
        self.root = (self.rsvd + self.nfat * self.spf) * self.bps
        self.data = self.root + self.rootent * 32
        self.csize = self.spc * self.bps
        self.nclusters = (self.spf * self.bps) // 2

    # ---- FAT ------------------------------------------------------------
    def get(self, n):
        return struct.unpack_from('<H', self.d, self.fat0 + n * 2)[0]

    def set(self, n, v):
        for i in range(self.nfat):
            off = self.fat0 + i * self.spf * self.bps + n * 2
            struct.pack_into('<H', self.d, off, v)

    def chain(self, start):
        out, c = [], start
        while 2 <= c < 0xFFF8:
            out.append(c)
            c = self.get(c)
            if len(out) > self.nclusters:
                raise ValueError('cyclic cluster chain')
        return out

    def free_chain(self, start):
        for c in self.chain(start):
            self.set(c, 0)

    def cluster_offset(self, n):
        return self.data + (n - 2) * self.csize

    def alloc_contiguous(self, count):
        """Find `count` consecutive free clusters."""
        run = 0
        for c in range(2, self.nclusters):
            if self.get(c) == 0:
                run += 1
                if run == count:
                    return c - count + 1
            else:
                run = 0
        raise ValueError('no room on the card for %d clusters' % count)

    def grow_to(self, end):
        if len(self.d) < end:
            self.d.extend(bytes(end - len(self.d)))

    # ---- root directory --------------------------------------------------
    def entries(self):
        for i in range(self.rootent):
            off = self.root + i * 32
            e = self.d[off:off + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5 or e[11] == 0x0F:
                continue
            yield i, off, e

    def find(self, name83):
        want = self._raw_name(name83)
        for i, off, e in self.entries():
            if bytes(e[0:11]) == want and not (e[11] & 0x08):
                return i, off
        return None, None

    def free_slot(self):
        for i in range(self.rootent):
            off = self.root + i * 32
            if self.d[off] in (0x00, 0xE5):
                return i, off
        raise ValueError('root directory is full')

    @staticmethod
    def _raw_name(name83):
        stem, _, ext = name83.partition('.')
        if len(stem) > 8 or len(ext) > 3:
            raise ValueError('not an 8.3 name: ' + name83)
        return (stem.upper().ljust(8) + ext.upper().ljust(3)).encode('ascii')

    def write_file(self, name83, payload):
        # drop any previous copy, so re-running replaces rather than duplicates
        i, off = self.find(name83)
        if off is not None:
            old = struct.unpack_from('<H', self.d, off + 26)[0]
            if old >= 2:
                self.free_chain(old)
            self.d[off:off + 32] = bytes(32)
        else:
            i, off = self.free_slot()

        nclust = max(1, -(-len(payload) // self.csize))
        start = self.alloc_contiguous(nclust)
        self.grow_to(self.cluster_offset(start + nclust))

        base = self.cluster_offset(start)
        self.d[base:base + len(payload)] = payload
        pad = nclust * self.csize - len(payload)
        if pad:                                   # blank the last cluster's tail
            self.d[base + len(payload):base + nclust * self.csize] = bytes(pad)

        for k in range(nclust):
            self.set(start + k, 0xFFFF if k == nclust - 1 else start + k + 1)

        date = ((STAMP.year - 1980) << 9) | (STAMP.month << 5) | STAMP.day
        time = (STAMP.hour << 11) | (STAMP.minute << 5) | (STAMP.second // 2)
        e = bytearray(32)
        e[0:11] = self._raw_name(name83)
        e[11] = 0x20                                   # archive
        struct.pack_into('<H', e, 14, time)            # created
        struct.pack_into('<H', e, 16, date)
        struct.pack_into('<H', e, 18, date)            # accessed
        struct.pack_into('<H', e, 22, time)            # modified
        struct.pack_into('<H', e, 24, date)
        struct.pack_into('<H', e, 26, start)
        struct.pack_into('<I', e, 28, len(payload))
        self.d[off:off + 32] = e
        return start, nclust


def main():
    raw = open(IMAGE, 'rb').read()
    volume, lba = unwrap(raw)
    print('input %d bytes, %s' % (
        len(raw), ('partitioned at LBA %d' % lba) if lba is not None else 'unpartitioned'))

    fs = Fat16(volume)
    print('volume: %d B/cluster | root at 0x%x | data at 0x%x' % (fs.csize, fs.root, fs.data))

    for name, rel in FILES.items():
        payload = open(os.path.join(SRC_ROOT, rel), 'rb').read()
        start, n = fs.write_file(name, payload)
        print('  + %-12s %7d bytes -> %d cluster(s) from %d' % (name, len(payload), n, start))

    for name in ROMS:
        payload = open(os.path.join(ROM_DIR, name), 'rb').read()
        start, n = fs.write_file(name, payload)
        print('  + %-12s %7d bytes -> %d cluster(s) from %d  (CHIP-8 ROM)'
              % (name, len(payload), n, start))

    for name, build in GENERATED.items():
        payload = build()
        start, n = fs.write_file(name, payload)
        print('  + %-12s %7d bytes -> %d cluster(s) from %d  (generated here)'
              % (name, len(payload), n, start))

    open(IMAGE, 'wb').write(wrap(bytes(fs.d)))

    # read it straight back and check everything round-trips
    print('\nverifying:')
    out = open(IMAGE, 'rb').read()
    vol, lba = unwrap(out)
    if lba is None:
        raise SystemExit('the written image has no usable partition table')
    print('  partition 1: type 0x%02x, %d sectors at LBA %d'
          % (out[450], struct.unpack_from('<I', out, 458)[0],
             struct.unpack_from('<I', out, 454)[0]))

    v = Fat16(vol)
    ok = struct.unpack_from('<I', vol, 28)[0] == PART_LBA
    if not ok:
        print('  BPB hidden-sector count does not match the partition start')
    for i, off, e in v.entries():
        stem = e[0:8].decode('latin1').rstrip()
        ext = e[8:11].decode('latin1').rstrip()
        if e[11] & 0x08:
            print('  volume label %s%s' % (stem, ext))
            continue
        size = struct.unpack_from('<I', e, 28)[0]
        chain = v.chain(struct.unpack_from('<H', e, 26)[0])
        got = b''.join(v.d[v.cluster_offset(c):v.cluster_offset(c) + v.csize]
                       for c in chain)[:size]
        full = stem + ('.' + ext if ext else '')
        if full in GENERATED:
            good = got == GENERATED[full]()
            note = 'matches generator' if good else 'MISMATCH'
            ok &= good
            print('  %-12s %8d bytes  %3d clusters  %s' % (full, size, len(chain), note))
            continue
        if full in ROMS:
            want = open(os.path.join(ROM_DIR, full), 'rb').read()
            print('  %-14s %6d bytes  %s' % (full, len(got),
                                             'ok' if got == want else 'MISMATCH'))
            continue
        exp = FILES.get(full)
        if exp:
            want = open(os.path.join(SRC_ROOT, exp), 'rb').read()
            good = got == want
            note = 'matches source' if good else 'MISMATCH'
        else:
            good = len(v.d) >= v.cluster_offset(max(chain)) + v.csize
            note = 'fully within image' if good else 'TRUNCATED'
        ok &= good
        print('  %-12s %8d bytes  %3d clusters  %s' % (full, size, len(chain), note))

    print('\nfinal image: %d bytes (%.2f MB)' % (len(out), len(out) / 1048576))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
