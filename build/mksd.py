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
SITE = r"C:\github\gamebuino_classic_games"
IMAGE = os.path.join(SITE, "webemulator", "sdcard.img")

# 8.3 name on the card  ->  file in the source archive
FILES = {
    # gamebuino-community-rpg: its map/text data and its sound bank
    'DATA.DAT': r'games\gamebuino-community-rpg\src\DATA.DAT',
    'SOUND.DAT': r'games\gamebuino-community-rpg\src\SOUND.DAT',
    # sd_map_test's tilemap
    'SDMAP.DAT': r'tools\sd_map_test\SDMAP.DAT',
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
