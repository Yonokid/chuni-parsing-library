"""Reader for E-mote PSB containers (.emtbytes). Layout per FreeMote (UlyssesWu/FreeMote, CC BY-NC-SA 4.0).

Only reading is implemented. The v3/v4 header is XorShift128-encrypted (HeaderEncrypt=1); the key is recovered from the
first word, whose plaintext is the header length.
"""
import struct
from dataclasses import dataclass, field

M = 0xFFFFFFFF
KEYS = (123456789, 362436069, 521288629)

# object type bytes
NULL, FALSE, TRUE, N0 = 1, 2, 3, 4  # numbers N1..N8 are 5..12
ARRAY1, STRING1, RESOURCE1, FLOAT0, FLOAT, DOUBLE, LIST, OBJECTS, EXTRA1 = 0x0D, 0x15, 0x19, 0x1D, 0x1E, 0x1F, 0x20, 0x21, 0x22


@dataclass
class Res:
    """Binary chunk reference (texture, ...); data is filled from the chunk tables."""
    index: int
    data: bytes = field(default=b"", repr=False)
    extra: bool = False


def _stream(key4: int, n: int) -> bytes:
    k1, k2, k3 = KEYS
    out = bytearray()
    while len(out) < n:
        a = (k1 ^ (k1 << 11)) & M
        c = (a ^ key4 ^ ((a ^ (key4 >> 11)) >> 8)) & M
        k1, k2, k3, key4 = k2, k3, key4, c
        out += struct.pack("<I", c)
    return bytes(out[:n])


def _recover_key(first_word: int, plain: int) -> int:
    """Invert the first cipher word (c = a ^ b ^ ((a ^ (b >> 11)) >> 8)) back to key4 (b)."""
    a = (KEYS[0] ^ (KEYS[0] << 11)) & M
    y = first_word ^ plain ^ a ^ (a >> 8)
    return (y ^ (y >> 19)) & M


def _read_header(b: bytes) -> dict:
    if b[:4] != b"PSB\0":
        raise ValueError("not a PSB file")
    version, encrypted = struct.unpack_from("<HH", b, 4)
    n = {1: 5, 2: 8, 3: 9, 4: 12}[version]  # words after the 8 byte preamble (v1 has fewer; only 3/4 seen)
    raw = b[8:8 + 4 * n]
    if encrypted:
        # plaintext word 0 is HeaderLength: 8 + 4*n = 56 for v4, 44 for v3; verify the rest via offset sanity
        plain = 8 + 4 * n
        key = _recover_key(struct.unpack_from("<I", raw)[0], plain)
        raw = bytes(x ^ y for x, y in zip(raw, _stream(key, len(raw))))
    w = struct.unpack(f"<{n}I", raw)
    h = dict(zip(("length", "names", "strings", "strings_data", "chunk_offsets", "chunk_lengths", "chunk_data",
                  "entries", "checksum", "extra_offsets", "extra_lengths", "extra_data"), w))
    if not (h["names"] < h["strings"] < h["strings_data"] <= h["chunk_offsets"] <= len(b)):
        raise ValueError("PSB header offsets implausible (wrong key guess or unsupported version)")
    return h


class _Reader:
    def __init__(self, b: bytes):
        self.b = b
        self.h = _read_header(b)
        self.pos = 0
        self._names()
        self.str_off = self._array_at(self.h["strings"])
        self.chunks = list(zip(self._array_at(self.h["chunk_offsets"]), self._array_at(self.h["chunk_lengths"])))
        self.extra = (list(zip(self._array_at(self.h["extra_offsets"]), self._array_at(self.h["extra_lengths"])))
                      if self.h.get("extra_offsets") else [])

    # -- primitives
    def u8(self) -> int:
        v = self.b[self.pos]
        self.pos += 1
        return v

    def uint(self, n: int) -> int:
        v = int.from_bytes(self.b[self.pos:self.pos + n], "little")
        self.pos += n
        return v

    def array(self, typ: int | None = None) -> list[int]:
        """Typed uint array: count (n bytes), entry-size byte, entries."""
        typ = self.u8() if typ is None else typ
        count = self.uint(typ - ARRAY1 + 1)
        size = self.u8() - 12
        return [self.uint(size) for _ in range(count)]

    def _array_at(self, off: int) -> list[int]:
        self.pos = off
        return self.array()

    def _names(self) -> None:
        self.pos = self.h["names"]
        charset, data, idx = self.array(), self.array(), self.array()
        self.names = []
        for i in idx:
            chars, c = [], data[i]
            while c:
                code = data[c]
                chars.append(c - charset[code])
                c = code
            self.names.append(bytes(reversed(chars)).decode("utf-8"))

    # -- values
    def value(self):
        t = self.u8()
        if t == NULL:
            return None
        if t in (FALSE, TRUE):
            return t == TRUE
        if t == N0:
            return 0
        if 5 <= t <= 12:
            n = t - 4
            v = int.from_bytes(self.b[self.pos:self.pos + n], "little", signed=True)
            self.pos += n
            return v
        if t == FLOAT0:
            return 0.0
        if t == FLOAT:
            v = struct.unpack_from("<f", self.b, self.pos)[0]
            self.pos += 4
            return v
        if t == DOUBLE:
            v = struct.unpack_from("<d", self.b, self.pos)[0]
            self.pos += 8
            return v
        if ARRAY1 <= t <= 0x14:
            return self.array(t)
        if 0x15 <= t <= 0x18:
            i = self.uint(t - STRING1 + 1)
            o = self.h["strings_data"] + self.str_off[i]
            return self.b[o:self.b.index(0, o)].decode("utf-8")
        if 0x19 <= t <= 0x1C:
            return self._res(self.uint(t - RESOURCE1 + 1), False)
        if 0x22 <= t <= 0x25:
            return self._res(self.uint(t - EXTRA1 + 1), True)
        if t == LIST:
            offs = self.array()
            base, out = self.pos, []
            for o in offs:
                self.pos = base + o
                out.append(self.value())
            self.pos = base + (max(offs) if offs else 0)  # callers always seek, end position isn't needed
            return out
        if t == OBJECTS:
            names, offs = self.array(), self.array()
            base, out = self.pos, {}
            for ni, o in zip(names, offs):
                self.pos = base + o
                out[self.names[ni]] = self.value()
            return out
        raise ValueError(f"unknown PSB type 0x{t:02x} at {self.pos - 1}")

    def _res(self, index: int, extra: bool) -> Res:
        off, length = (self.extra if extra else self.chunks)[index]
        start = self.h["extra_data" if extra else "chunk_data"] + off
        return Res(index, self.b[start:start + length], extra)

    def root(self):
        self.pos = self.h["entries"]
        return self.value()


def load_psb(path: str):
    """Returns the root dict; binary chunks appear as Res objects."""
    with open(path, "rb") as f:
        return _Reader(f.read()).root()


def _jsonable(v):
    if isinstance(v, Res):
        return {"$res": v.index}
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    return v


def _dxt5_image(data: bytes, width: int, height: int):
    """Raw DXT5 blocks -> PIL image, via a minimal DDS header so Pillow does the decode."""
    from io import BytesIO
    from PIL import Image
    hdr = struct.pack("<4sIIIIIII44sII4s20s", b"DDS ", 124, 0x81007, height, width, len(data), 0, 1, b"\0" * 44,
                      32, 4, b"DXT5", b"\0" * 20) + struct.pack("<I16s", 0x1000, b"\0" * 16)
    return Image.open(BytesIO(hdr + data))


def export_emote(path: str, out_dir: str, name: str) -> dict:
    """Writes <name>.json (the motion tree, binary chunks replaced by {"$res": index}) and one webp per texture atlas.

    Each source (`tex`, or `tex#000`... for models with several atlases) gets its `texture.pixel` replaced by the webp
    file name: <name>.webp for a lone `tex`, <name>_<n>.webp (n = order of the sources) otherwise.
    """
    import json
    import os
    root = load_psb(path)
    sources = {k: v for k, v in root.get("source", {}).items() if isinstance(v, dict) and "texture" in v}
    for n, (key, src) in enumerate(sources.items()):
        tex = src["texture"]
        if tex.get("type") != "DXT5" or not isinstance(tex.get("pixel"), Res):
            continue
        img = _dxt5_image(tex["pixel"].data, tex["width"], tex["height"])
        tex["pixel"] = f"{name}.webp" if len(sources) == 1 else f"{name}_{n}.webp"
        img.save(os.path.join(out_dir, tex["pixel"]))
    with open(os.path.join(out_dir, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(_jsonable(root), f, ensure_ascii=False)
    return root
