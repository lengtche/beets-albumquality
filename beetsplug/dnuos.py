import os
import re
import struct
import sys
import glob

class MP3:
    brtable = (
        # MPEG 2/2.5
        (
            # Layer III
            (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0),
            # Layer II
            (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0),
            # Layer I
            (0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224,
             256, 0)
        ), 
        # MPEG 1
        (
            # Layer III
            (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256,
             320, 0),
            # Layer II
            (0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320,
             384, 0),
            # Layer I
            (0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384,
             416, 448, 0)
        )
    )

    fqtable = ((32000, 16000,  8000), # MPEG 2.5
               (    0,     0,     0), # Reserved
               (22050, 24000, 16000), # MPEG 2  
               (44100, 48000, 32000)) # MPEG 1  
    

    def __init__(self, track_path):
        self._f = open(track_path, 'rb')
        self.filesize = os.path.getsize(track_path)

        self._begin = None
        self._end = None
        self._meta = []
        self.mp3header = self.getheader(self.stream_begin())

        self.time = 9
        self.brtype = "CV"[self.mp3header[1] in ('Xing', 'VBRI')]
        self.framesync = (self.mp3header[0] >> 21 & 2047)
        self.versionindex = (self.mp3header[0] >> 19 & 3)
        self.layerindex = (self.mp3header[0] >> 17 & 3)
        self.protectionbit = (self.mp3header[0] >> 16 & 1)
        bitrateindex = (self.mp3header[0] >> 12 & 15)
        frequencyindex = (self.mp3header[0] >> 10 & 3)
        self.paddingbit = (self.mp3header[0] >> 9 & 1)
        self.privatebit = (self.mp3header[0] >> 8 & 1)
        self.modeindex = (self.mp3header[0] >> 6 & 3)
        self.modeextindex = (self.mp3header[0] >> 4 & 3)
        self.copyrightbit = (self.mp3header[0] >> 3 & 1)
        self.originalbit = (self.mp3header[0] >> 2 & 1)
        self.emphasisindex = (self.mp3header[0] & 3)
        self.framesize = self.mp3header[4]
        self.vendor = self.mp3header[6]
        # if self.vendor == 'UUUUUUUUU':
        #     self.vendor = ''
        # else:
        #     for char in self.vendor:
        #         if char not in string.printable:
        #             self.vendor = ''
        #             break
        self.freq =  self.fqtable[self.versionindex][frequencyindex]
        self.channels = (2, 2, 2, 1)[self.modeindex]

        if self.brtype == "V":
            if self.framesize <= 0:
                self.framesize = self.stream_end() - self.stream_begin()
            self.framecount = self.mp3header[3] + 1
            self._bitrate = int(1000.0 * self.framesize * self.freq /
                                float(self.modificator() * self.framecount))
        else:
            self._bitrate = int(1000.0 * self.brtable[self.versionindex &
                                1][self.layerindex-1][bitrateindex])
            self.framecount = int(self.streamsize() * self.freq /
                                  float(self.modificator() * self._bitrate)
                                  * 1000)
        self.time = self.streamsize() * 8.0 / self._bitrate
        # self._f.seek(0)

        # try:
        #     self.id3v1 = dnuos.id3.ID3v1(self._f)
        # except dnuos.id3.Error:
        #     self.id3v1 = None

        # try:
        #     self.id3v2 = dnuos.id3.ID3v2(self._f,
        #                                  limit_frames=self.id3v2_frames)
        # except dnuos.id3.Error:
        #     self.id3v2 = None
    def modificator(self):

        if self.layerindex == 3:
            return 12000
        else:
            return 144000
    def streamsize(self):
        if self.brtype == 'V':
            return self.framesize
        else:
            return self.stream_end() - self.stream_begin()

    def stream_begin(self):
        if self._begin != None:
            return self._begin

        mark = self._f.tell()
        self._begin = 0
        # import pdb;pdb.set_trace()
        # check for prepended ID3v2
        self._f.seek(0)
        if self._f.read(3) == b'ID3':
            self._meta.append((0, "ID3v2"))
            data = struct.unpack("<2x5B", self._f.read(7))
            self._begin += 10 + unpack_bits(data[-4:])
            if data[0] & 0x40:
                extsize = struct.unpack("<4B", self._f.read(4))
                self._begin += unpack_bits(extsize)
            if data[0] & 0x10:
                self._begin += 10

        self._f.seek(mark)
        return self._begin

    def stream_end(self):

        if self._end != None:
            return self._end

        mark = self._f.tell()
        self._end = self.filesize

        # check for ID3v1
        # self._f.seek(-128, 2)
        # if self._f.read(3) == "TAG":
        #     self._end -= 128
        #     self._meta.append((self._end, "ID3v1"))

        # # check for appended ID3v2
        # self._f.seek(self._end - 10)
        # if self._f.read(3) == "3DI":
        #     data = struct.unpack("<2x5B", self._f.read(7))
        #     self._end -= 20 + unpack_bits(data[-4:])
        #     if data[0] & 0x40:
        #         extsize = struct.unpack("<4B", self._f.read(4))
        #         self._end -= unpack_bits(extsize)
        #         self._meta.append((self._end, "ID3v2"))

        self._f.seek(mark)
        return self._end

    _search_sync = re.compile(b'\xff[\xe0-\xff]').search
    _search_info = re.compile(b'(Xing|Info|VBRI)').search

    def valid(self, header):
        return (((header>>21 & 2047) == 2047) and
            ((header>>19 &  3) != 1) and
            ((header>>17 &  3) != 0) and
            ((header>>12 & 15) != 0) and
            ((header>>12 & 15) != 15) and
            ((header>>10 &  3) != 3) and
            ((header     &  3) != 2))

    def getheader(self, offset=0):
        _search_sync = self._search_sync
        _search_info = self._search_info

        # Setup header and sync stuff
        overlap = 1
        # frame header + presumed padding + xing/info header (oh god)
        pattern1 = '>l32x4s3l100xL9s2B8x2B5xH'
        # xing/info header
        pattern2 = '>4s3l100xL9s2B8x2B5xH' # 5xH adds preset info
        # vbri header
        pattern3 = '>4s6x2l'
        pattern1size = struct.calcsize(pattern1)
        pattern2size = struct.calcsize(pattern2)
        pattern3size = struct.calcsize(pattern3)

        # Read first block
        self._f.seek(offset)
        start = self._f.tell()
        chunk = self._f.read(1024 + overlap)
        # import pdb;pdb.set_trace()
        # Do all file if we have to
        while len(chunk) > overlap:
            # Look for sync
            sync = _search_sync(chunk)
            while sync:
                # Read header
                self._f.seek(start + sync.start())
                header = struct.unpack(pattern1, self._f.read(pattern1size))
                if self.valid(header[0]):
                    info = _search_info(chunk)
                    while info:
                        self._f.seek(start + info.start())
                        if info.group() == 'VBRI':
                            data = struct.unpack(pattern3,
                                    self._f.read(pattern3size))
                            return (header[0], data[0], None, data[2],
                                    data[1], None, 'Fraunhofer')
                        return (header[0],) + struct.unpack(pattern2,
                                                self._f.read(pattern2size))
                    return header

                # How about next sync in this block?
                sync = _search_sync(chunk, sync.start() + 1)

            # Read next chunk
            start = start + 1024
            self._f.seek(start + overlap)
            chunk = chunk[-overlap:] + self._f.read(1024)
        if offset >= self.filesize - 2:
            raise SpacerError("Spacer found %s" % self._f.name)
        self._f.seek(offset)
        tag = struct.unpack(">3s", self._f.read(struct.calcsize(">3s")))
        if tag[0] == "TAG":
            raise SpacerError("Spacer found %s" % self._f.name)

    def profile(self):
        if not hasattr(self, 'mp3header'):
            raise Exception('mp3header not set!')            
        if self.mp3header[6][:4] == b'LAME':
            try:
                major, minor = ''.join(map(chr, self.mp3header[6][4:8])).split('.', 1) # join byte array
                version = (int(major), int(minor))
            except ValueError:
                version = (-1, 0)
            vbrmethod = self.mp3header[7] & 15
            lowpass = self.mp3header[8]
            ath = self.mp3header[9] & 15
            preset = self.mp3header[11] & 0x1ff

            if preset > 0:
                if preset == 320:
                    return "-b 320"
                elif preset in (410, 420, 430, 440, 450, 460, 470, 480, 490,
                                500):
                    if vbrmethod == 4:
                        return "-V%dn" % ((500 - preset) / 10)
                    else:
                        return "-V%d" % ((500 - preset) / 10)
                # deprecated values?
                elif preset == 1000:
                    return "-r3mix"
                elif preset == 1001:
                    return "-aps"
                elif preset == 1002:
                    return "-ape"
                elif preset == 1003:
                    return "-api"
                elif preset == 1004:
                    return "-apfs"
                elif preset == 1005:
                    return "-apfe"
                elif preset == 1006:
                    return "-apm"
                elif preset == 1007:
                    return "-apfm"
            elif version < (3, 90) and version > (0, 0):
                if vbrmethod == 8:  # unknown
                    if lowpass in (97, 98):
                        if ath == 0:
                            return "-r3mix"
            elif version >= (3, 90) and version < (3, 97):
                if vbrmethod == 3:  # vbr-old / vbr-rh
                    if lowpass in (195, 196):
                        if ath in (2, 4):
                            return "-ape"
                    elif lowpass == 190:
                        if ath == 4:
                            return "-aps"
                    elif lowpass == 180:
                        if ath == 4:
                            return "-apm"
                elif vbrmethod == 4: # vbr-mtrh
                    if lowpass in (195, 196):
                        if ath in (2, 4):
                            return "-apfe"
                        elif ath == 3:
                            return "-r3mix"
                    elif lowpass == 190:
                        if ath == 4:
                            return "-apfs"
                    elif lowpass == 180:
                        if ath == 4:
                            return "-apfm"
                elif vbrmethod in (1, 2): # abr
                    if lowpass in (205, 206):
                        if ath in (2, 4):
                            return "-api"
        # else:
        return '%i %s' % (int(self._bitrate) / 1000, self.brtype)   

def unpack_bits(bits):
    """Unpack ID3's syncsafe 7bit number format."""
    value = 0
    for chunk in bits:
        value = value << 7
        value = value | chunk
    return value