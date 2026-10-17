"""Readers for the stevia/yabukita model containers inside stage .afb files."""
import struct

REF_BASE = 10001  # object references are stored as index + 10001; 0 is null


def avts(data: bytes) -> dict[str, tuple[int, bytes]]:
    """Chunk name -> (kind, bytes). Kinds: 0 YABX, 1 DDS, 2 VBO, 3 IBO. Magic is AVTS (svo) or CVU (uvc)."""
    assert data[:4] in (b"AVTS", b"CVU\0"), data[:4]
    chunks = {}
    if data[:4] == b"CVU\0":  # .uvc: unnamed entries {kind, index, size, offset} every 0x100 bytes from 0x80
        for i in range(struct.unpack_from("<I", data, 4)[0]):
            kind, index, size, offset = struct.unpack_from("<4I", data, 0x80 + 0x100 * i)
            chunks[f"{kind}_{index}"] = (kind, data[offset:offset + size])
        return chunks
    for i in range(struct.unpack_from("<I", data, 4)[0]):
        entry = 0x80 + 0x400 * i
        name = data[entry:entry + 0x200].split(b"\0")[0].decode()
        kind, _index, size, offset = struct.unpack_from("<4I", data, entry + 0x200)
        chunks[name] = (kind, data[offset:offset + size])
    return chunks


class _Reader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def take(self, fmt: str):
        value = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += struct.calcsize(fmt)
        return value[0]

    def raw(self, n: int) -> bytes:
        self.pos += n
        return self.data[self.pos - n:self.pos]

    def string(self, short: bool = True) -> str:
        return self.raw(self.take("<b" if short else "<h")).rstrip(b"\0").decode("utf-8", "replace")


def read_yabx(data: bytes) -> list[dict]:
    """Objects as {"_class": name, field: raw bytes}; fields of parent classes are included."""
    r = _Reader(data)
    assert r.raw(4) == b"YABX"
    r.raw(12)  # s16 version 1, s16 0, u32 size, u32 crc
    while r.take("<B"):
        r.string(short=False)  # tags
    r.string()  # root name
    while r.string():
        r.take("<I")  # library versions
    classes = [None]
    while name := r.string():
        _flags, parent = r.take("<B"), r.take("<h")
        fields = []
        while field := r.string():
            r.take("<B")  # flags (bit 0: required)
            fields.append((field, r.take("<h")))  # size 0 = variable length, u32-prefixed
        classes.append((name, parent, fields))
    while r.string():
        r.take("<h")  # named objects
    while r.string():
        pass  # string table
    objects = []
    for _ in range(r.take("<h")):
        class_id, size = r.take("<h"), r.take("<I")
        end = r.pos + size
        obj, c = {"_class": classes[class_id][0]}, class_id
        while c:
            for field, field_size in classes[c][2]:
                obj[field] = r.raw(field_size or r.take("<I"))
            c = classes[c][1]
        assert r.pos == end, obj["_class"]
        objects.append(obj)
    return objects


# Field value decoders (variable-length fields keep their u32 length stripped; strings are s16 len + bytes).
def f_str(v: bytes) -> str:
    return v[2:].rstrip(b"\0").decode("utf-8", "replace")

def f_int(v: bytes) -> int:
    return struct.unpack("<i", v)[0]

def f_floats(v: bytes) -> tuple[float, ...]:
    return struct.unpack(f"<{len(v) // 4}f", v)

def f_ref(v: bytes) -> int | None:
    i = struct.unpack("<h", v)[0]
    return i - REF_BASE if i else None

def f_refs(v: bytes) -> list[int]:
    return [i - REF_BASE for i in struct.unpack_from(f"<{struct.unpack_from('<I', v)[0]}H", v, 4)]


if __name__ == "__main__":
    import sys
    data = open(sys.argv[1], "rb").read()
    chunks = avts(data)
    objects = read_yabx(next(d for kind, d in chunks.values() if kind == 0))
    assert objects[0]["_class"] in ("stevia::Database", "uva::AnimDatabase")
    for i, o in enumerate(objects):
        print(i, o["_class"], {k: len(v) for k, v in o.items() if k != "_class"})
