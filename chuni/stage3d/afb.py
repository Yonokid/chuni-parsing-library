import os
from dataclasses import dataclass
from amlibpy.stream import Stream


@dataclass
class File:
    offset: int
    length: int
    b: int
    c: int
    content: Stream

    path: str = ""
    name: str = ""


class AFxC_Reader(Stream):
    def read_pof0(self):
        assert self.str(4) == "POF0"
        length = self.u32()
        offset = self.u32()
        assert offset == 0x20
        self.skip(20)

        pof_length = self.u32() - 4
        pof_data = []
        while pof_length:
            data = self.u8()
            if not data:
                break

            flags = data & 0xC0
            if flags == 0x40:
                pof_data.append(data & 0x3F)
                pof_length -= 1
            elif flags == 0x80:
                data <<= 8
                data |= self.u8()
                pof_data.append(data & 0x3FFF)
                pof_length -= 2
            elif flags == 0xC0:
                data <<= 24
                data |= self.u8() << 16
                data |= self.u8() << 8
                data |= self.u8()
                pof_data.append(data & 0x3FFFFFFF)
                pof_length -= 4

        return pof_data


class AFNC_Reader(AFxC_Reader):
    def read_afnc(self):
        assert self.str(4) == "AFNC"
        length = self.u32()
        offset = self.u32()
        assert offset == 0x20
        self.skip(20)

        assert self.read(4) == b"\xB9\x9B\xED\x77"
        off = self.u32()  # 30h
        self.u32()  # 7B60h
        count = self.u32()

        for i in range(count):
            block = self[offset + off + 0x60 * i:]

            print(hex(offset + off + 0x60 * i))

        # Filenames start at 7BE0?


        # Skip past ourself
        self.seek(length + offset)
        # TODO: What _is_ POF0
        pof0 = self.read_pof0()


class AFRC_Reader(AFxC_Reader):
    def read_afrc(self) -> list[File]:
        assert self.str(4) == "AFRC"
        length = self.u32()
        offset = self.u32()
        assert offset == 0x20
        self.skip(20, null=False)

        # Header
        assert self.read(4) == b"\xB9\x9B\xED\x77"
        self.u32()  # Count of something
        count = self.u32()

        files = []

        for _ in range(count):
            file_offset = self.u32()
            file_length = self.u32()
            b = self.u32()
            c = self.u32()

            files.append(
                File(file_offset, file_length, b, c, content=self[file_offset : file_offset + file_length])
            )

        # Not always null: seen non-zero reserved/padding bytes here when count is small.
        self.skip(20, null=False)
        for i in files:
            i.path = self.str_z()
            i.name = self.str_z()

        # Skip past ourself
        self.seek(length + offset)
        # TODO: What _is_ POF0
        pof0 = self.read_pof0()

        return files


class AcroReader(Stream):
    def read_file(self):
        start = self.tell()

        assert self.str(4) == "FILE"
        length = self.u32()
        offset = self.u32()
        assert offset == 0x20
        self.skip(12)
        self.u32()  # File end?
        self.skip(4)

        self.seek(length, 1)

        return self[start + offset : start + offset + length]

    def read_filenames(self):
        start = self.tell()
        assert self.str(4) == "FLNM"
        self.u32()  # 0x20
        self.u32()  # 0x20
        self.skip(12)
        self.u32()  # 0x40
        self.skip(4)

        names = self.read(0x20)  # Which one is this from?

    def read_eofc(self):
        assert self.str(4) == "EOFC"
        self.skip(4)
        assert self.u32() == 0x20
        self.skip(20)

    def read_file_system(self):
        start = self.tell()

        assert self.str(4) == "FILS"
        length = self.u32()
        file_offset = self.u32()
        self.skip(8)

        self.u32()  # Looks like file_offset again? (abs start?)
        self.u32()  # Looks like length + offset?   (abs end?)
        self.skip(4)
        file_count = self.u32()
        self.i32()
        self.u32()
        self.skip(20)

        self.seek(start + file_offset)

        files = []
        for _ in range(file_count):
            files.append(self.read_file())

        names = self.read_filenames()

        self.read_eofc()

        # Assert EOF
        assert self.read(1) == b""

        return files, names


def extract_svo_textures(data: bytes) -> list[tuple[str, bytes]]:
    names = []
    i = 0
    while True:
        pos = 0x480 + 1024 * (i - 1)
        if pos >= len(data):
            break
        terminator = data.find(b"\x00", pos)
        end = terminator if terminator != -1 else len(data)
        text = data[pos:end].decode("ascii", errors="replace")
        if text.startswith("YABX"):
            break
        if text.endswith(".dds"):
            names.append(text)
        i += 1

    positions = []
    start = 0
    while True:
        idx = data.find(b"DDS ", start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1

    textures = []
    for n, pos in enumerate(positions):
        if n >= len(names):
            break
        end = positions[n + 1] if n + 1 < len(positions) else len(data)
        textures.append((names[n], data[pos:end]))

    return textures


if __name__ == "__main__":
    acro = AcroReader(open("scripts/acro/mmo_vv_y11_maimai_walk.afb", "rb"))

    files, names = acro.read_file_system()
    assert len(files) == 2

    # Just trust tbh
    afnc = AFNC_Reader(files[0])
    afrc = AFRC_Reader(files[1])

    afnc_files = afnc.read_afnc()
    afrc_files = afrc.read_afrc()

    os.makedirs("scripts/acro/out", exist_ok=True)
    for i in afrc_files:
        # print(i.name)
        open("scripts/acro/out/" + i.name, "wb").write(i.content.read(i.length))
