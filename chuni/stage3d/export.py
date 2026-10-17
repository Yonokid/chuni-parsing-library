"""Export a stage .afb (st_*.afb / nf_*.afb) to an animated .glb for three.js."""
import io
import json
import math
import os
import struct

from PIL import Image

from chuni.stage3d.afb import AcroReader, AFRC_Reader
from chuni.stage3d.yabx import avts, f_floats, f_int, f_ref, f_refs, f_str, read_yabx

MODEL_TYPE = 6001001  # star::SglBasicModel
PROP_SVO, PROP_TEXTURES, PROP_MOTION = 200, 300, 400  # model properties: svo, textures, .uvc it plays


def read_afb(path: str) -> tuple[bytes, set[int], list[tuple[str, bytes]]]:
    """(AFNC chunk bytes incl. header, pointer locations from POF0, AFRC resources in index order)."""
    files, _ = AcroReader(open(path, "rb")).read_file_system()
    afnc = files[0].read(1 << 30)
    resources = [(e.name, e.content.read(e.length)) for e in AFRC_Reader(files[1]).read_afrc()]
    return afnc, _pof0(afnc), resources


def _pof0(chunk: bytes) -> set[int]:
    length, offset = struct.unpack_from("<II", chunk, 4)
    p = offset + length
    assert chunk[p:p + 4] == b"POF0"
    pof_len, pof_off = struct.unpack_from("<II", chunk, p + 4)
    pof = chunk[p + pof_off:p + pof_off + pof_len]
    end, i, cur, ptrs = struct.unpack_from("<I", pof)[0], 4, 0, set()
    while i < end:
        b = pof[i]
        if b & 0xC0 == 0x40:
            v, i = b & 0x3F, i + 1
        elif b & 0xC0 == 0x80:
            v, i = (b & 0x3F) << 8 | pof[i + 1], i + 2
        elif b & 0xC0 == 0xC0:
            v, i = int.from_bytes(bytes([b & 0x3F]) + pof[i + 1:i + 4], "big"), i + 4
        else:
            break
        cur += v * 4
        ptrs.add(cur)
    return ptrs


MODULE_MATRIX, MODULE_TEXTURE = 100, 6002003  # MomMatrix, texture-slot module
CAMERA_TYPE = 6000001
PARTICLE_TYPES = {6001008, 205, 209}
TIME_RATE_TYPE = 6001016
PRIMITIVE_TYPE = 100
SCREEN_PRIMITIVE_TYPE = 200
SCREEN_FILL_TYPE = 6001020  # Sgl2dPrimitiveFill: a Sgl2DPrimitive stretched over the screen
LIGHT_TYPES = {6001100: "ambient", 6001101: "parallel", 6001102: "point", 6001104: "fog"}
FILTER_TYPES = {
    6001203: ("bloom", 17, {"threshold": 1, "intensity": 2}),  # BloomRange, BloomInten
    6001205: ("color", 7, {"color": 1, "saturation": 2, "brightness": 3, "contrast": 4, "gamma": 5, "power": 6}),
    6001213: ("bloom2", 30, {"retina": 1, "threshold": 2, "intensity": 4}),  # BloomRetinaRatio, BloomRange, BloomIntensity
}
PROPAGATES = {2, 3, MODEL_TYPE}
GAME_CAMERA = {"eye": (0.0, 57.0, 44.0), "target": (0.0, 3.0, -146.5), "fov": 27.5, "near": 1.0, "far": 1500.0}


def _mul(a: list[float], b: list[float]) -> list[float]:
    """4x4 column-major product a @ b."""
    return [sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]


def _translate(x, y, z):
    return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1]


def _scale(x, y, z):
    # Some keys flatten models with a 0 axis (Steins;Gate gears); glTF needs an invertible matrix.
    x, y, z = (v if v else 1e-6 for v in (x, y, z))
    return [x, 0, 0, 0, 0, y, 0, 0, 0, 0, z, 0, 0, 0, 0, 1]


def _rotate(x, y, z):
    """Degrees; the engine builds Rz·Ry·Rx (0x153f340), i.e. three.js Euler order 'ZYX'."""
    import math
    cx, sx, cy, sy, cz, sz = (f(math.radians(v)) for v in (x, y, z) for f in (math.cos, math.sin))
    rx = [1, 0, 0, 0, 0, cx, sx, 0, 0, -sx, cx, 0, 0, 0, 0, 1]
    ry = [cy, 0, -sy, 0, 0, 1, 0, 0, sy, 0, cy, 0, 0, 0, 0, 1]
    rz = [cz, sz, 0, 0, -sz, cz, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    return _mul(_mul(rz, ry), rx)


IDENTITY = _scale(1, 1, 1)


def _key_value(key: tuple) -> list[float] | None:
    """Vector A at t = 0: static keys use A, random-static keys the middle of A..B, animated keys start at 0."""
    mode, a, b = key[0], list(key[13:16]), key[17:20]
    if mode == 0:
        return a
    if mode == 4:
        v = [(p + q) / 2 for p, q in zip(a, b)]
        return [v[0]] * 3 if key[5] else v
    return None


def _look_at(eye, target) -> list[float]:
    """Camera-to-world matrix looking from eye to target (glTF cameras look down -Z, +Y up)."""
    z = [e - t for e, t in zip(eye, target)]
    n = sum(v * v for v in z) ** 0.5 or 1
    z = [v / n for v in z]
    x = [z[2], 0.0, -z[0]]  # up (0, 1, 0) x z
    n = sum(v * v for v in x) ** 0.5 or 1
    x = [v / n for v in x]
    y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]]
    return x + [0] + y + [0] + z + [0] + list(eye) + [1]


def _matrix_key(key: tuple) -> list[float] | None:
    """Initial (t = 0) matrix of one MomMatrix key (0x74 bytes; update 0x1dca320, setup 0x1dc9ce0).

    [0] motion: 0 static, 1 velocity, 2/6 acceleration, 3/7 oscillation; 4-7 pick values at random between
    vector A [13..15] and B [17..19] ([5] set = one scalar for all axes). [1] target: 0 translate, 1 rotate
    (degrees), 2 scale (animated modes scale by 1 + value). Only static modes move anything at t = 0.
    ponytail: random modes use the midpoint of their range; animated modes are left at their start value.
    """
    target, v = key[1], _key_value(key)
    if target == 0:
        return _translate(*v) if v else None
    if target == 1:
        return _rotate(*v) if v else None
    if target == 2:
        return _scale(*v) if v else None
    return None  # target >= 100: not a transform


def scene_tree(afnc: bytes, ptrs: set[int]) -> dict:
    """AFNC node tree from the root: {"type", "index", "matrix", "svo", "textures", "lanes", "children"}.

    Node records are 0x60 bytes: +0 type, +0x24 index, +0x3c properties, +0x40 module lanes (+0x44 count),
    +0x48 state-independent module list {first, count}, +0x50 first child, +0x54 next sibling. Lanes are states ({id, ?, ?, -1, -1, first module, count, next}); id -1 always applies
    and 0 is the initial state. Modules are {type, ..., +0x20 next, +0x24 info}. A MomMatrix info is
    {u32 what, u32 count, ptr keys}: what 0 moves the node, 1/2 are a camera's eye/target.
    """
    u32 = lambda o: struct.unpack_from("<I", afnc, o)[0]
    s32 = lambda o: struct.unpack_from("<i", afnc, o)[0]
    ptr = lambda o: u32(o) if o in ptrs else 0
    cstr = lambda o: afnc[o:afnc.index(b"\0", o)].decode("utf-8", "replace")
    seen = set()

    f32 = lambda o: struct.unpack_from("<f", afnc, o)[0]

    def lanes(node):
        lane, n = ptr(node + 0x40), 0
        while lane and n < 64:
            mods, m = [], ptr(lane + 0x14)
            while m and len(mods) < 256:
                mods.append(m)
                m = ptr(m + 0x20)
            yield s32(lane), mods
            lane, n = ptr(lane + 0x1C), n + 1
        common = ptr(node + 0x48)  # {ptr first module, u32 count}: modules active in every state
        if common and ptr(common):
            # ponytail: on some nodes this points at node records instead; keep only module records
            mods, m = [], ptr(common)
            while m and len(mods) < 256 and u32(m) in (100, 106, 250, 300, 401, 402, 403, 600, 751):
                mods.append(m)
                m = ptr(m + 0x20)
            yield -1, mods

    def modules(node):
        for lane_id, mods in lanes(node):
            if lane_id in (-1, 0):
                yield from mods

    def keys(info):
        out, base = [], ptr(info + 8)
        for k in range(u32(info + 4) if base else 0):
            o = base + 0x74 * k
            i, f = struct.unpack_from("<29i", afnc, o), struct.unpack_from("<29f", afnc, o)
            out.append(tuple(f[n] if n in (6, 7) or n >= 9 else i[n] for n in range(29)))  # [6]/[7] times
        return out

    def anim_module(m) -> dict | None:
        """Raw data of the modules stage_anim.py simulates."""
        info, kind = ptr(m + 0x24), u32(m)
        if not info:
            return None
        if kind == MODULE_MATRIX:
            return {"type": kind, "what": s32(info), "keys": keys(info)}
        if kind == 106:  # MomMatrixGoal (0x1dccc80 / update 0x1dccf60)
            entries, base = [], ptr(info)
            for e in range(u32(info + 4) if base else 0):
                o = base + 0x5C * e
                entries.append({"goal": struct.unpack_from("<3f", afnc, o), "alt": struct.unpack_from("<3f", afnc, o + 16),
                                "start": f32(o + 0x20), "channel": s32(o + 0x24), "interp": s32(o + 0x28),
                                "duration": f32(o + 0x2C), "duration_max": f32(o + 0x30), "ease": s32(o + 0x38),
                                "power": f32(o + 0x3C), "random": s32(o + 0x54)})
            return {"type": kind, "entries": entries, "target": s32(info + 8), "mode": s32(info + 12),
                    "loops": s32(info + 16), "accumulate": s32(info + 20), "total": f32(info + 0x24)}
        if kind == 751:  # MomChangeState (update 0x1de0c80; actions 0x1db1f90)
            acts = ptr(info + 0x14)
            return {"type": kind, "repeat": s32(info), "condition": s32(info + 4), "value": s32(info + 8),
                    "actions": [struct.unpack_from("<7i", afnc, acts + 0x1C * a) for a in range(u32(info + 0x18) if acts else 0)]}
        return None

    def argb(word: int) -> list[float]:
        """D3DCOLOR (ARGB) -> [r, g, b, a] in 0..1."""
        return [(word >> sh & 0xFF) / 255 for sh in (16, 8, 0, 24)]

    def light(node) -> dict:
        """Light parameters from the class block (+0x5c): {u32 name ptr, 1, class fields..., colour properties}.

        A colour property is {101, 0, 0, 0, ptr..., u32 ARGB}: ambient has one, parallel/point have diffuse then
        specular, fog one. Point starts with its range (2 floats), fog with mode + min/max distance. A MomMaterial
        (300, keys of 0x28 bytes: [0] ARGB, [3] mode) on the node overrides the first colour.
        """
        kind, block = LIGHT_TYPES[u32(node)], ptr(node + 0x5C)
        colors, o = [], block
        while block and o < block + 0x100 and len(colors) < 2:
            if u32(o) == 101 and u32(o + 4) == u32(o + 8) == u32(o + 12) == 0:
                o += 16
                while o in ptrs or u32(o) == 0:
                    o += 4
                colors.append(argb(u32(o)))
            o += 4
        for m in modules(node):
            info = ptr(m + 0x24)
            if u32(m) == 300 and info and ptr(info + 0x10) and u32(info + 0xC):
                colors[:1] = [argb(u32(ptr(info + 0x10)))]
        out = {"kind": kind, "colors": colors}
        if kind == "point":
            out["range"] = [f32(block + 8), f32(block + 12)]
        if kind == "fog":
            out["range"] = [f32(block + 12), f32(block + 16)]
        return out

    def post_filter(node) -> dict | None:
        """Filter parameter block (+0x5c): {name, 1, ?, u32 loop, static fields..., u32 key count, ptr keys}.

        Keys hold the keyable params in ctor order (bools such as BloomEnable are static fields instead); word 0
        is frames to reach the key (float), colours are ARGB. Output {"kind", "loop", "params": names, "keys": [[seconds,
        values...]]} with the colour flattened to r, g, b.
        """
        kind, size, fields = FILTER_TYPES[u32(node)]
        b = ptr(node + 0x5C)
        o = next((o for o in range(b + 0x10, b + 0x40, 4) if o in ptrs), 0)
        if not o:
            return None
        names, keys, t = [], [], 0.0
        for name in fields:
            names += [f"{name}.{c}" for c in "rgb"] if name == "color" else [name]
        for k in range(u32(o - 4)):
            key = ptr(o) + 4 * size * k
            t += max(f32(key), 0.0)
            values = []
            for name, word in fields.items():
                values += argb(u32(key + 4 * word))[:3] if name == "color" else [f32(key + 4 * word)]
            keys.append([t / 60] + values)
        return {"kind": kind, "loop": bool(u32(b + 0xC)), "params": names, "keys": keys} if keys else None

    def primitive(node, textures: list[int]) -> dict:
        """SglPrimitive block (+0x5c): +0xc quad count, +0x10/+0x18 width/height (+0x14/+0x1c random maxima,
        +0x20 keep aspect), +0x30 mode (0 quads, 2 particle-like), then a colour property; textures = property 300.
        ponytail: one centred quad per node; counts > 1 (scattered quads) and mode 2 are drawn as one quad.
        Sgl2DPrimitive (200) has integer width/height at +0x10/+0x14 and an origin mode at +0 (0 screen centre, y up;
        2 top-left, y down, as the data suggests); its matrix is in 1920x1080 pixels.
        """
        b = ptr(node + 0x5C)
        if u32(node) == SCREEN_FILL_TYPE:  # its 50x50 size is a placeholder
            return {"width": 1920.0, "height": 1080.0, "count": 1, "mode": 0, "screen": 0,
                    "textures": [t for t in textures if t >= 0], "color": [1.0, 1.0, 1.0, 1.0]}
        if u32(node) == SCREEN_PRIMITIVE_TYPE:  # {+0 origin mode, ..., +0xc priority, +0x10 s32 w, +0x14 s32 h, ...}
            width, height = float(s32(b + 0x10)), float(s32(b + 0x14))
        else:
            width, height = f32(b + 0x10), f32(b + 0x18)
        if u32(node) != SCREEN_PRIMITIVE_TYPE and s32(b + 0x20):
            height = width * height / (f32(b + 0x10) or 1)
        color, o = [1.0, 1.0, 1.0, 1.0], b
        while o < b + 0x100:
            if u32(o) == 101 and u32(o + 4) == u32(o + 8) == u32(o + 12) == 0:
                o += 16
                while o in ptrs or u32(o) == 0:
                    o += 4
                color = argb(u32(o))
                break
            o += 4
        out = {"width": width, "height": height, "count": s32(b + 0xC), "mode": s32(b + 0x30),
               "textures": [t for t in textures if t >= 0], "color": color}
        if u32(node) == SCREEN_PRIMITIVE_TYPE:
            out["screen"] = s32(b)
        return out

    def particles(node, textures: list[int]) -> dict:
        """SglBasicParticle emitter block (+0x5c), as far as decoded (ctor 0x161e0e0 feeds sea's emitter):
        five {count, ptr} lists at +0..+0x24: A colour keys over life (0x1c: {type, ARGB, ARGB random max, 1,
        frame}), B size-multiplier keys (0x20: {type, min, max, 0, 0, frame}), C initial velocity (0x34: min vec3,
        max vec3), D acceleration (0x28: min vec3, max vec3), E (8 bytes, unknown); +0x30 shape (2/11/12 box with full size +0x34..+0x3c, 3 disc radius +0x34,
        else sphere radius +0x34), +0x54 max particles, +0x7c lifetime (frames), +0x80/+0x84 start size (+ random max),
        +0x88/+0x8c end size, +0xbc/+0xc0 sprite-sheet cols/rows, +0xc8 frame count, +0xcc frame time.
        ponytail: list E, the remaining flags and blend mode aren't decoded; without colour keys the viewer fades
        particles in and out over their life. Colour is also multiplied by the node's MomMaterial tint.
        """
        b = ptr(node + 0x5C)

        def vec_range(count_off, size):
            if not u32(b + count_off) or not ptr(b + count_off + 4):
                return [[0.0] * 3, [0.0] * 3]
            q = ptr(b + count_off + 4)
            return [list(struct.unpack_from("<3f", afnc, q)), list(struct.unpack_from("<3f", afnc, q + 0x10))]

        velocity, acceleration = vec_range(0x10, 0x34), vec_range(0x18, 0x28)
        q = ptr(b + 4)  # list A: colour over life {type, ARGB, ARGB random max, 1, frame}
        colors = [[f32(q + 0x1C * i + 0x10)] + argb(u32(q + 0x1C * i + 4)) for i in range(u32(b))] if q else []
        if not any(any(c[1:]) for c in colors):
            colors = []  # all transparent black: treated as "no colour keys" (otherwise the gear clouds vanish)
        q = ptr(b + 0xC)  # list B: size multiplier over life {type, min, max, 0, 0, frame}
        scales = [[f32(q + 0x20 * i + 0x14), (f32(q + 0x20 * i + 4) + f32(q + 0x20 * i + 8)) / 2] for i in range(u32(b + 8))] if q else []
        start, end = f32(b + 0x80), f32(b + 0x88)
        return {"shape": s32(b + 0x30), "size": list(struct.unpack_from("<3f", afnc, b + 0x34)),
                "count": s32(b + 0x54), "life": f32(b + 0x7c),
                "startSize": [start, max(f32(b + 0x84), start) if f32(b + 0x84) >= 0 else start],
                "endSize": [end, max(f32(b + 0x8c), end) if f32(b + 0x8c) >= 0 else end],
                "velocity": velocity, "acceleration": acceleration, "colors": colors, "scales": scales,
                "cols": max(s32(b + 0xbc), 1), "rows": s32(b + 0xc0),
                "frames": s32(b + 0xc8), "frameTime": f32(b + 0xcc), "textures": [t for t in textures if t >= 0]}

    def uv_modules(node) -> list[dict]:
        """MomTexturePatternAnimation (401), MomUvSet (402), MomUvScroll (403) of a node; speeds are per frame.

        401 info: [0..1] image range, [2] random image, [5] order (0 row-major, 1 column-major, 2 rect list),
        [6] cols, [7] rows, [8] frames per cell, [9..10] cell range, [11] direction (0 fwd, 1 back, 2 random),
        [12] start cell (<0 random), [13] loop, [14] uv set, [15]/[16] rect list (x0, y0, x1, y1).
        402 info: [0] uv set (-1 all), [1] mode (0 fixed rect, 1 moving rect), [2..5] rect, [6..7] velocity,
        [9] flags (bit 0/1: u1/v1 are sizes). 403 info: [0] mode (0 set, 1 scroll, 2 oscillate, 3 add once,
        4 add per update), [1] uv set, [2] interval, [3] phase, [4..5] speed or point A, [6..7] point B.
        """
        stateful = any(u32(m) == 751 for _, mods in lanes(node) for m in mods)
        out = []
        for lane_id, mods in lanes(node):
            if lane_id != -1 and (lane_id != 0 or stateful):
                continue
            for m in mods:
                info, kind = ptr(m + 0x24), u32(m)
                if not info or kind not in (401, 402, 403):
                    continue
                i = lambda k: s32(info + 4 * k)
                fl = lambda k: f32(info + 4 * k)
                if kind == 401:
                    rects = [list(struct.unpack_from("<4f", afnc, ptr(info + 60) + 16 * r)) for r in range(i(16))] if ptr(info + 60) else []
                    out.append({"kind": "flip", "images": [i(0), i(1)], "randomImage": bool(i(2)), "order": i(5),
                                "cols": max(i(6), 1), "rows": i(7) if i(7) > 0 else max(i(6), 1), "interval": fl(8),
                                "cells": [i(9), i(10)], "direction": i(11), "start": i(12), "loop": bool(i(13)),
                                "set": i(14), "rects": rects})
                elif kind == 402:
                    out.append({"kind": "rect", "set": i(0), "mode": i(1), "rect": [fl(2), fl(3), fl(4), fl(5)],
                                "velocity": [fl(6), fl(7)], "relative": i(9)})
                else:
                    out.append({"kind": "scroll", "mode": i(0), "set": i(1), "interval": fl(2), "phase": fl(3),
                                "speed": [fl(4), fl(5)], "end": [fl(6), fl(7)]})
        return out

    def tint(node) -> dict | None:
        """MomMaterial (300) colour multiplier of a node as {"keys": [[seconds, r, g, b, a], ...], "loop": bool}.

        Keys (0x28 bytes): [0]/[1] ARGB A/B, [3] mode (0 A; 1-4 random between A and B -> midpoint; 5 oscillate
        A<->B with period [4] frames), [8] frames to reach this key from the previous one. Info: keys at +0x10,
        count +0xc, loop +0x18. None when it is constant white.
        ponytail: tints in state lanes restart whenever the state is re-entered, which the viewer can't replay
        yet, so lane-0 tints are only used on nodes that never change state.
        """
        stateful = any(u32(m) == 751 for _, mods in lanes(node) for m in mods)
        for m in (mods for lane_id, ms in lanes(node) if lane_id == -1 or lane_id == 0 and not stateful for mods in ms):
            info = ptr(m + 0x24)
            if u32(m) != 300 or not info or not ptr(info + 0x10) or not u32(info + 0xC):
                continue
            base, keys, t = ptr(info + 0x10), [], 0.0
            for k in range(u32(info + 0xC)):
                o = base + 0x28 * k
                a, b, mode = argb(u32(o)), argb(u32(o + 4)), s32(o + 12)
                t += max(f32(o + 0x20), 0.0)
                if mode == 5 and f32(o + 0x10) > 0:  # oscillation: sample one period
                    period = f32(o + 0x10)
                    keys += [[(t + period * i / 8) / 60] + [x + (y - x) * (0.5 - 0.5 * math.cos(2 * math.pi * i / 8))
                                                            for x, y in zip(a, b)] for i in range(9)]
                    t += period
                else:
                    keys.append([t / 60] + (a if mode == 0 else [(x + y) / 2 for x, y in zip(a, b)]))
            loop = bool(s32(info + 0x18)) or any(s32(base + 0x28 * k + 12) == 5 for k in range(u32(info + 0xC)))
            if len(keys) == 1 and keys[0][1:] == [1.0, 1.0, 1.0, 1.0]:
                return None
            return {"keys": keys, "loop": loop}
        return None

    def visit(node, rate: float = 1.0) -> dict:
        seen.add(node)
        if u32(node) == TIME_RATE_TYPE and (b := ptr(node + 0x5C)):
            rate *= f32(b + 0x10)
        props, p = {}, ptr(ptr(node + 0x3C) + 0x10) if ptr(node + 0x3C) else 0
        while p and len(props) < 64:  # {u32 id, u32, ptr data, u32 count, ptr next}
            data, count = ptr(p + 8), u32(p + 12)
            props[u32(p)] = [s32(data + 8 * i) for i in range(count)] if data else []
            p = ptr(p + 16)
        matrix, slots, look = IDENTITY, {}, {}
        for m in modules(node):
            info = ptr(m + 0x24)
            if not info:
                continue
            if u32(m) == MODULE_TEXTURE and ptr(info + 4):  # info {+4 placeholder name, +0x10 slot}
                slots[cstr(ptr(info + 4))] = u32(info + 0x10)
            elif u32(m) == MODULE_MATRIX:
                what = s32(info)
                for key in keys(info):
                    if what == 0 and (op := _matrix_key(key)):
                        matrix = _mul(matrix, op)
                    elif what in (1, 2) and key[1] == 0 and (v := _key_value(key)):
                        look["eye" if what == 1 else "target"] = tuple(v)
        textures = props.get(PROP_TEXTURES, [])
        out = {"type": u32(node), "index": s32(node + 0x24), "matrix": matrix,
               "svo": props[PROP_SVO][0] if u32(node) == MODEL_TYPE and props.get(PROP_SVO) else -1,
               "motion": props[PROP_MOTION][0] if u32(node) == MODEL_TYPE and props.get(PROP_MOTION) else -1,
               "textures": {name: textures[i] for name, i in slots.items() if i < len(textures) and textures[i] >= 0},
               "children": [], "rate": rate,
               "lanes": [(lane_id, [a for m in mods if (a := anim_module(m))]) for lane_id, mods in lanes(node)]}
        if u32(node) in LIGHT_TYPES:
            out["light"] = light(node)
        elif u32(node) in FILTER_TYPES and ptr(node + 0x5C) and (f := post_filter(node)):
            out["filter"] = f
        elif (t := tint(node)) is not None:
            out["tint"] = t
        if u32(node) in PARTICLE_TYPES and ptr(node + 0x5C):
            out["particles"] = particles(node, props.get(PROP_TEXTURES, []))
        # untextured fills (flat colour flashes?) stay unexported
        textured = any(t >= 0 for t in props.get(PROP_TEXTURES, []))
        if (u32(node) in (PRIMITIVE_TYPE, SCREEN_PRIMITIVE_TYPE) or u32(node) == SCREEN_FILL_TYPE and textured) \
                and ptr(node + 0x5C):
            out["primitive"] = primitive(node, props.get(PROP_TEXTURES, []))
        if uv := uv_modules(node):
            out["uv"] = uv
        if u32(node) == CAMERA_TYPE:  # active only with both eye and target (SglCamera ctor 0x1d95390)
            params, cam = ptr(node + 0x5C), dict(GAME_CAMERA)
            if "eye" in look and "target" in look:
                cam.update(look)
            for name, off in (("fov", 0xC), ("near", 0x10), ("far", 0x14)):
                if params and (v := struct.unpack_from("<f", afnc, params + off)[0]) > 0:
                    cam[name] = v
            out["camera"] = cam
        child = ptr(node + 0x50)
        while child and child not in seen:
            out["children"].append(visit(child, rate))
            child = ptr(child + 0x54)
        return out

    return visit(ptr(0x24))


def scene_models(tree: dict) -> list[dict]:
    """Every SglBasicModel node in the tree."""
    found = [tree] if tree["type"] == MODEL_TYPE else []
    for child in tree["children"]:
        found += scene_models(child)
    return found


def _row_major(b: tuple) -> list[float]:
    """3x4 row-major matrix (translation in the last column) -> 4x4 column-major."""
    return [b[0], b[4], b[8], 0, b[1], b[5], b[9], 0, b[2], b[6], b[10], 0, b[3], b[7], b[11], 1]


def _skeleton(objs: list[dict]) -> list[dict]:
    """stevia::Node list of an svo: name, parent (index into the list), blend index, rest TRS, inverse bind."""
    nodes = [i for i, o in enumerate(objs) if o["_class"] == "stevia::Node"]
    where = {obj: n for n, obj in enumerate(nodes)}
    out = []
    for i in nodes:
        o = objs[i]
        b = f_floats(o["_mtxBind"])  # 3x4 row-major, translation in the last column
        mesh = f_ref(o["_mesh"])
        out.append({"name": f_str(o["_name"]), "parent": where.get(f_ref(o["_parent"])),
                    "shapes": f_refs(objs[mesh]["_shape"]) if mesh is not None else [],
                    "blend": f_int(o["_blendIndex"]), "translation": list(f_floats(o["_translation"])),
                    "rotation": list(f_floats(o["_quaternion"])), "scale": list(f_floats(o["_scale"])),
                    "ibm": _row_major(b)})
    return out


def _strip_to_triangles(idx: list[int]) -> list[int]:
    tris = []
    for i in range(len(idx) - 2):
        a, b, c = idx[i:i + 3]
        if a == b or b == c or a == c:
            continue
        tris += (a, b, c) if i % 2 == 0 else (a, c, b)
    return tris


# VertexElement semantics -> glTF attribute; element type -> byte size
_ATTR = {0: "POSITION", 3: "NORMAL", 5: "TEXCOORD", 10: "COLOR_0"}
_SIZE = {1: 8, 2: 12, 8: 4}


class _Glb:
    def __init__(self):
        self.bin = bytearray()
        self.gltf = {"asset": {"version": "2.0", "generator": "chuni-parsing-library stage3d"},
                     "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "materials": [],
                     "textures": [], "images": [], "samplers": [{"wrapS": 10497, "wrapT": 10497}],
                     "accessors": [], "bufferViews": [], "buffers": [{"byteLength": 0}]}

    def view(self, data: bytes, target: int | None = None) -> int:
        self.bin += b"\0" * (-len(self.bin) % 4)
        v = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target:
            v["target"] = target
        self.bin += data
        self.gltf["bufferViews"].append(v)
        return len(self.gltf["bufferViews"]) - 1

    def accessor(self, data: bytes, ctype: int, count: int, type_: str, target: int, **extra) -> int:
        self.gltf["accessors"].append({"bufferView": self.view(data, target), "componentType": ctype,
                                       "count": count, "type": type_, **extra})
        return len(self.gltf["accessors"]) - 1

    def write(self, path: str):
        g = self.gltf
        g["buffers"][0]["byteLength"] = len(self.bin)
        if not g["scenes"][0]["nodes"]:
            del g["scenes"][0]["nodes"]
        if "extensions" in g and not g["extensions"].get("KHR_lights_punctual", {}).get("lights"):
            del g["extensions"]
        for key in [k for k, v in g.items() if isinstance(v, list) and not v]:
            del g[key]
        if "textures" not in g:
            g.pop("samplers", None)
        js = json.dumps(g, separators=(",", ":")).encode()
        js += b" " * (-len(js) % 4)
        self.bin += b"\0" * (-len(self.bin) % 4)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, 28 + len(js) + len(self.bin)))
            f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
            f.write(struct.pack("<II", len(self.bin), 0x004E4942) + bytes(self.bin))


class _StageExporter:
    def __init__(self, resources: list[tuple[str, bytes]]):
        self.resources = resources
        self.glb = _Glb()
        self.images: dict[str, int | None] = {}  # dds name -> texture index
        self.opaque: dict[str, bool] = {}  # dds name -> no transparency at all
        self.meshes: dict[tuple, int] = {}  # (svo name, swaps) -> mesh index
        self.vertex_cache: dict[tuple, dict[str, int]] = {}
        self.node_ids: dict[int, int] = {}  # id(scene tree node) -> glTF node
        self.skeletons: dict[str, list[dict]] = {}  # svo name -> its stevia::Node list
        self.ibms: dict[str, int] = {}  # svo name -> inverse bind matrix accessor
        self.svo_objs: dict[str, list[dict]] = {}  # svo name -> its YABX objects
        self.motions: list[tuple[str, int, dict[int, list[tuple]]]] = []  # baked .uvc clips

    def texture(self, name: str, dds: bytes) -> int | None:
        if name not in self.images:
            try:
                img = Image.open(io.BytesIO(dds))
                img.load()
            except Exception:
                self.images[name] = None
                return None
            img = img.convert("RGBA")
            self.opaque[name] = img.getchannel("A").getextrema()[0] == 255
            webp = io.BytesIO()
            img.save(webp, "WEBP", quality=90)  # ~10x smaller than PNG for these

            g = self.glb.gltf
            g["images"].append({"bufferView": self.glb.view(webp.getvalue()), "mimeType": "image/webp", "name": name})
            g["textures"].append({"sampler": 0, "extensions": {"EXT_texture_webp": {"source": len(g["images"]) - 1}}})
            for key in ("extensionsUsed", "extensionsRequired"):
                if "EXT_texture_webp" not in g.setdefault(key, []):
                    g[key].append("EXT_texture_webp")
            self.images[name] = len(g["textures"]) - 1
        return self.images[name]

    def material(self, objs: list[dict], state: dict, chunks: dict, swaps: dict[str, int]) -> int:
        mat = {"name": f_str(state["_name"]), "pbrMetallicRoughness": {"metallicFactor": 0, "roughnessFactor": 1}}
        params = {f_str(objs[i]["_name"]): objs[f_ref(objs[i]["_value"])] for i in f_refs(state["_userParameter"])}
        spec_map = None
        for t in f_refs(state["_texture"]):
            tex = objs[t]
            image = objs[f_ref(tex["_image"])]
            kind, uv = f_str(tex["_textureType"]), f_int(tex["_uvSetIndex"])
            if kind not in ("base", "normal", "specular"):
                continue  # environment maps: no glTF slot
            name = f_str(image["_fileName"])
            dds = self.resources[swaps[name]][1] if name in swaps else chunks.get(f_str(image["_chunkFileName"]), (0, b""))[1]
            got = self.texture(self.resources[swaps[name]][0] if name in swaps else name, dds)
            if got is None:
                continue
            if kind == "base" and uv == 0:
                mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": got}
            elif kind == "base":  # the second base layer on uv set 1 is the baked occlusion map (_oc)
                mat["occlusionTexture"] = {"index": got, "texCoord": uv}
            elif kind == "normal":
                mat["normalTexture"] = {"index": got}
            elif kind == "specular":
                spec_map = {"index": got} if uv == 0 else None
        fill = f_int(state["_fillType"])  # stevia::FillType: kFILL_OPAQUE, kFILL_PUNCHTHROUGH, kFILL_TRANSPARENT
        if fill == 1:
            mat["alphaMode"], mat["alphaCutoff"] = "MASK", f_int(state["_alphaRef"]) / 255
        elif fill == 2:
            mat["alphaMode"] = "BLEND"
        if f_int(state["_blendFactorDst"]) == 1:  # kBLENDFACTOR_ONE: additive; glTF can't say so, the viewer reads extras
            mat["alphaMode"], mat["extras"] = "BLEND", {"additive": True}
        if f_str(state["_lighting"]) == "constant":
            mat["extensions"] = {"KHR_materials_unlit": {}}
            used = self.glb.gltf.setdefault("extensionsUsed", [])
            if "KHR_materials_unlit" not in used:
                used.append("KHR_materials_unlit")
        if f_int(state["_cullMode"]) == 2 or state["_transparentDoubleSide"][0]:  # kCULLMODE_CW / CCW / NONE
            mat["doubleSided"] = True
        # Specular: lambert and black-specular materials have none (glTF's default would add a 4% sheen); phong
        # uses the specular colour (x tsSpecularScale), its _sp map, and a roughness from the Blinn exponent.
        lighting = f_str(state["_lighting"])
        spec = list(f_floats(params["specular"]["_valueColor"])[:3]) if "specular" in params else [0, 0, 0]
        scale = f_floats(params["tsSpecularScale"]["_valueF32"])[0] if "tsSpecularScale" in params else 1
        if lighting != "constant":
            ext = {"specularFactor": 0.0}
            if lighting == "phong" and any(spec):
                ext = {"specularColorFactor": [min(c * scale, 1.0) for c in spec]}
                if spec_map:
                    ext["specularColorTexture"] = spec_map
                shininess = f_floats(params["shininess"]["_valueF32"])[0] if "shininess" in params else 20
                mat["pbrMetallicRoughness"]["roughnessFactor"] = (2 / (shininess + 2)) ** 0.5
            mat.setdefault("extensions", {})["KHR_materials_specular"] = ext
            used = self.glb.gltf.setdefault("extensionsUsed", [])
            if "KHR_materials_specular" not in used:
                used.append("KHR_materials_specular")
        factor = list(f_floats(params["diffuse"]["_valueColor"])[:3]) if "diffuse" in params else [1, 1, 1]
        factor.append(f_floats(params["opacity"]["_valueF32"])[0] if "opacity" in params else 1)
        if factor != [1, 1, 1, 1]:
            mat["pbrMetallicRoughness"]["baseColorFactor"] = [min(max(x, 0), 1) for x in factor]
        mat["_vertexColor"] = bool(params.get("tsEnableVertexColor") and f_int(params["tsEnableVertexColor"]["_valueS32"]))
        g = self.glb.gltf
        g["materials"].append(mat)
        return len(g["materials"]) - 1

    def vertex_attrs(self, objs: list[dict], vb: dict, vbo: bytes, vertex_color: bool) -> dict[str, int]:
        """glTF accessors for a vertex buffer, shared by every primitive drawing from it."""
        key = (f_str(vb["_chunkFileName"]), len(vbo), vertex_color)
        if key in self.vertex_cache:
            return dict(self.vertex_cache[key])
        stride, count = f_int(vb["_stride"]), f_int(vb["_vertexNumber"])
        attrs, offset, blend = {}, 0, []
        for e in f_refs(objs[f_ref(vb["_vertexDeclaration"])]["_vertexElement"]):
            el = objs[e]
            sem, typ, index = f_int(el["_semantics"]), f_int(el["_elementType"]), f_int(el["_index"])
            size = _SIZE[typ]
            col = b"".join(vbo[i * stride + offset:i * stride + offset + size] for i in range(count))
            offset += size
            name = _ATTR.get(sem)
            if name == "POSITION":
                floats = struct.unpack(f"<{count * 3}f", col)
                lo = [min(floats[k::3]) for k in range(3)]
                hi = [max(floats[k::3]) for k in range(3)]
                attrs[name] = self.glb.accessor(col, 5126, count, "VEC3", 34962, min=lo, max=hi)
            elif name == "NORMAL":  # UBYTE4N in xyz order (or plain float3) -> float3
                normals = []
                xyz = struct.unpack(f"<{count * 3}f", col) if size == 12 else \
                    [col[i + k] / 127.5 - 1 for i in range(0, len(col), 4) for k in range(3)]
                for i in range(0, len(xyz), 3):
                    x, y, z = xyz[i:i + 3]
                    length = (x * x + y * y + z * z) ** 0.5  # some files store unnormalized normals
                    normals += (x / length, y / length, z / length) if length > 1e-6 else (0, 1, 0)
                attrs[name] = self.glb.accessor(struct.pack(f"<{count * 3}f", *normals), 5126, count, "VEC3", 34962)
            elif name == "TEXCOORD" and index < 2:
                attrs[f"TEXCOORD_{index}"] = self.glb.accessor(col, 5126, count, "VEC2", 34962)
            elif name == "COLOR_0" and vertex_color:  # D3DCOLOR (BGRA) -> RGBA
                rgba = bytes(col[i + k] for i in range(0, len(col), 4) for k in (2, 1, 0, 3))
                attrs[name] = self.glb.accessor(rgba, 5121, count, "VEC4", 34962, normalized=True)
            elif sem in (1, 2):
                blend.append(col)
        assert offset == stride, (offset, stride)
        if blend:  # W elements hold (weight, blend index) byte pairs: [w0 i0 w1 i1] [w2 i2 w3 i3]
            joints, weights = bytearray(), []
            for v in range(count):
                pairs = [(col[4 * v + 2 * p], col[4 * v + 2 * p + 1]) for col in blend for p in range(2)][:4]
                pairs += [(0, 0)] * (4 - len(pairs))
                total = sum(w for w, _ in pairs) or 1
                joints += bytes(i if w else 0 for w, i in pairs)
                weights += [w / total for w, _ in pairs]
            attrs["JOINTS_0"] = self.glb.accessor(bytes(joints), 5121, count, "VEC4", 34962)
            attrs["WEIGHTS_0"] = self.glb.accessor(struct.pack(f"<{count * 4}f", *weights), 5126, count, "VEC4", 34962)
        self.vertex_cache[key] = attrs
        return dict(attrs)

    def primitive(self, objs: list[dict], shape: dict, chunks: dict, swaps: dict[str, int]) -> dict | None:
        batch = objs[f_ref(shape["_batch"])]
        vb = objs[f_refs(batch["_vertexBufferList"])[0]]
        ib = objs[f_ref(batch["_indexBuffer"])]
        vbo = chunks[f_str(vb["_chunkFileName"])][1]
        ibo = chunks[f_str(ib["_chunkFileName"])][1]
        ifmt = "<%dI" if f_int(ib["_indexType"]) else "<%dH"
        isize = 4 if f_int(ib["_indexType"]) else 2
        start, n = f_int(batch["_indexStart"]), f_int(batch["_indexNumber"])
        indices = list(struct.unpack_from(ifmt % n, ibo, start * isize))
        prim_type = f_int(batch["_primitiveType"])  # kPRIMITIVE_TRIANGLES = 3, kPRIMITIVE_TRIANGLESTRIP = 4
        assert prim_type in (3, 4), prim_type
        tris = _strip_to_triangles(indices) if prim_type == 4 else indices
        if not tris:
            return None
        material = self.material(objs, objs[f_ref(shape["_state"])], chunks, swaps)
        vertex_color = self.glb.gltf["materials"][material].pop("_vertexColor")
        attrs = self.vertex_attrs(objs, vb, vbo, vertex_color)
        mat = self.glb.gltf["materials"][material]
        for slot in ("occlusionTexture", "normalTexture"):
            if slot in mat and f"TEXCOORD_{mat[slot].get('texCoord', 0)}" not in attrs:
                del mat[slot]
        if "TEXCOORD_0" not in attrs:
            mat["pbrMetallicRoughness"].pop("baseColorTexture", None)
        big = max(tris) > 0xFFFF
        idx = self.glb.accessor(struct.pack(f"<{len(tris)}{'I' if big else 'H'}", *tris),
                                5125 if big else 5123, len(tris), "SCALAR", 34963)
        return {"attributes": attrs, "indices": idx, "material": material}

    def objects(self, svo_name: str, svo: bytes) -> list[dict]:
        if svo_name not in self.svo_objs:
            self.svo_objs[svo_name] = read_yabx(next(d for kind, d in avts(svo).values() if kind == 0))
        return self.svo_objs[svo_name]

    def mesh(self, svo_name: str, svo: bytes, swaps: dict[str, int], shapes: tuple = ()) -> int | None:
        """Mesh of an svo (every Shape, or only the given Shape object indices)."""
        g = self.glb.gltf
        key = (svo_name, tuple(sorted(swaps.items())), shapes)
        if key not in self.meshes:
            chunks = avts(svo)
            objs = read_yabx(next(d for kind, d in chunks.values() if kind == 0))
            prims = [p for i, o in enumerate(objs) if o["_class"] == "stevia::Shape" and (not shapes or i in shapes)
                     if (p := self.primitive(objs, o, chunks, swaps))]
            self.meshes[key] = None
            if prims:  # glTF forbids meshes without primitives
                g["meshes"].append({"name": svo_name, "primitives": prims})
                self.meshes[key] = len(g["meshes"]) - 1
            if any("JOINTS_0" in p["attributes"] for p in prims):
                self.skeletons[svo_name] = _skeleton(objs)

        return self.meshes[key]

    def node(self, tree: dict) -> int | None:
        """glTF node for an AFNC subtree, or None when it holds no models."""
        res = self.resources
        mesh = rig = None
        if 0 <= tree["svo"] < len(res):
            svo_name, svo = res[tree["svo"]]
            objs = self.objects(svo_name, svo)
            skinned = any(o["_class"] == "stevia::VertexElement" and f_int(o["_semantics"]) in (1, 2) for o in objs)
            rig = None if skinned else self.rigid(svo_name, tree)  # rigid motion: the svo's nodes carry the shapes
            if rig is None:
                mesh = self.mesh(svo_name, svo, tree["textures"])
        children = [i for c in tree["children"] if (i := self.node(c)) is not None] + (rig or [])
        g = self.glb.gltf
        if "camera" in tree and "cameras" not in g:  # first camera only: the stage's background camera
            cam = tree["camera"]
            g["cameras"] = [{"type": "perspective", "name": "stage", "perspective": {
                "yfov": cam["fov"] * 3.141592653589793 / 180, "znear": cam["near"], "zfar": cam["far"]}}]
            g["nodes"].append({"name": "stage camera", "camera": 0, "matrix": _look_at(cam["eye"], cam["target"])})
            children.append(len(g["nodes"]) - 1)
        if "filter" in tree:  # post effects of the scene, in tree order
            g["scenes"][0].setdefault("extras", {}).setdefault("filters", []).append(tree["filter"])
        if (light := tree.get("light")) and light["colors"]:
            r, gr, b, a = light["colors"][0]
            if light["kind"] in ("ambient", "fog"):  # no glTF equivalent: scene extras for the viewer
                extras = g["scenes"][0].setdefault("extras", {})
                if light["kind"] == "ambient":
                    extras.setdefault("ambient", [r, gr, b, a])
                else:
                    extras.setdefault("fog", {"color": [r, gr, b], "max": a, "near": light["range"][0], "far": light["range"][1]})
            else:
                lights = g.setdefault("extensions", {}).setdefault("KHR_lights_punctual", {"lights": []})["lights"]
                entry = {"type": "directional" if light["kind"] == "parallel" else "point", "color": [r, gr, b], "intensity": a}
                if light["kind"] == "point":
                    entry["range"] = light["range"][1]
                lights.append(entry)
                used = g.setdefault("extensionsUsed", [])
                if "KHR_lights_punctual" not in used:
                    used.append("KHR_lights_punctual")
                ln = {"name": light["kind"], "extensions": {"KHR_lights_punctual": {"light": len(lights) - 1}}}
                matrix = tree["matrix"]  # a light's own matrix places/aims it (it isn't passed to children)
                if light["kind"] == "parallel":
                    # sea::LightParallel "Direction" defaults to (0, 1, 0) (ctor 0x5bd430) and is turned by the node
                    # matrix: the vector towards the light is R·+Y. glTF lights shine along -Z, so map +Z onto +Y.
                    matrix = _mul(matrix, _rotate(-90, 0, 0))
                if matrix != IDENTITY:
                    ln["matrix"] = matrix
                g["nodes"].append(ln)
                children.append(len(g["nodes"]) - 1)
        if (part := tree.get("particles")) and part["textures"] and part["count"] > 0:
            tex = self.texture(*res[part["textures"][0]]) if 0 <= part["textures"][0] < len(res) else None
            if tex is not None:  # an emitter node: the viewer simulates it (extras.particles), placed by its matrix
                # ponytail: the blend flag isn't decoded; glow sprites without alpha only make sense added
                additive = self.opaque.get(res[part["textures"][0]][0], False)
                en = {"name": "particles", "extras": {"particles": {**part, "texture": tex, "tint": tree.get("tint"),
                                                                    "additive": additive, "rate": tree["rate"]}}}
                if tree["matrix"] != IDENTITY:
                    en["matrix"] = tree["matrix"]
                g["nodes"].append(en)
                children.append(len(g["nodes"]) - 1)
        if (prim := tree.get("primitive")) and prim["textures"]:
            pn = self.primitive_node(tree, prim)
            if pn is not None:
                children.append(pn)
        if mesh is None and not children:
            return None
        node = {"name": f"{tree['type']}#{tree['index']}"}
        if rig is not None:
            node["name"] = res[tree["svo"]][0]
        if mesh is not None:
            node["mesh"], node["name"] = mesh, res[tree["svo"]][0]
            if (bones := self.skeletons.get(svo_name)) is not None:
                node["skin"], roots = self.skin(svo_name, bones, tree)
                children += roots
        if children:
            node["children"] = children
        if tree["matrix"] != IDENTITY and tree["type"] in PROPAGATES:
            node["matrix"] = tree["matrix"]
        if tree.get("tint"):  # colour/alpha multiplier for the meshes under this node (viewer applies it)
            node.setdefault("extras", {})["tint"] = tree["tint"]
        if 0 <= tree.get("motion", -1) < len(res) and res[tree["motion"]][0].lower().endswith(".uvc"):
            from chuni.stage3d.anim import uv_motion
            if uvm := uv_motion(res[tree["motion"]][1]):  # .uvc UV offset animation of the model
                tree["uv"] = tree.get("uv", []) + [uvm]
        if tree.get("uv"):  # UV scroll / rect / flipbook for the meshes under this node (viewer applies it)
            node.setdefault("extras", {})["uv"] = tree["uv"]
        if "extras" in node and tree["rate"] != 1:  # SglTimeRate: tint / uv time runs this many times faster
            node["extras"]["rate"] = tree["rate"]
        g["nodes"].append(node)
        self.node_ids[id(tree)] = len(g["nodes"]) - 1
        return len(g["nodes"]) - 1

    def skin(self, svo_name: str, bones: list[dict], tree: dict) -> tuple[int, list[int]]:
        """Joint nodes (one set per model instance) and a glTF skin; bakes the model's .uvc motion onto them."""
        g = self.glb.gltf
        first = len(g["nodes"])
        for b in bones:
            g["nodes"].append({"name": b["name"], "translation": b["translation"], "rotation": b["rotation"], "scale": b["scale"]})
        for i, b in enumerate(bones):
            if b["parent"] is not None:
                g["nodes"][first + b["parent"]].setdefault("children", []).append(first + i)
        joints = sorted((b["blend"], i) for i, b in enumerate(bones) if b["blend"] >= 0)
        if svo_name not in self.ibms:
            flat = [x for _, i in joints for x in bones[i]["ibm"]]
            self.ibms[svo_name] = self.glb.accessor(struct.pack(f"<{len(flat)}f", *flat), 5126, len(joints), "MAT4", None)
        g.setdefault("skins", []).append({"joints": [first + i for _, i in joints], "inverseBindMatrices": self.ibms[svo_name]})
        if 0 <= tree["motion"] < len(self.resources) and self.resources[tree["motion"]][0].lower().endswith(".uvc"):
            from chuni.stage3d.anim import motion, sample_motion
            frames, nodes = motion(self.resources[tree["motion"]][1])
            by_name = {b["name"]: (first + i, b) for i, b in enumerate(bones)}
            tracks = {by_name[n][0]: sample_motion(m, frames, by_name[n][1]["rotation"])
                      for n, m in nodes.items() if n in by_name}
            if tracks and frames:
                self.motions.append((f"motion {self.resources[tree['motion']][0]}", frames, tracks, tree["rate"]))
        return len(g["skins"]) - 1, [first + i for i, b in enumerate(bones) if b["parent"] is None]

    def rigid(self, svo_name: str, tree: dict) -> list[int] | None:
        """For an unskinned svo whose .uvc animates its nodes: the svo node tree with each node's shapes under it."""
        if not (0 <= tree["motion"] < len(self.resources)) or not self.resources[tree["motion"]][0].lower().endswith(".uvc"):
            return None
        from chuni.stage3d.anim import motion, sample_motion
        frames, nodes = motion(self.resources[tree["motion"]][1])
        objs = self.objects(svo_name, self.resources[tree["svo"]][1])
        bones = _skeleton(objs)
        if not frames or not any(b["name"] in nodes for b in bones):
            return None
        g, first = self.glb.gltf, len(self.glb.gltf["nodes"])
        for b in bones:
            g["nodes"].append({"name": b["name"], "translation": b["translation"], "rotation": b["rotation"], "scale": b["scale"]})
        for i, b in enumerate(bones):
            if b["parent"] is not None:
                g["nodes"][first + b["parent"]].setdefault("children", []).append(first + i)
            for shape in b["shapes"]:  # vertices are in model space: undo the node's bind pose
                if (m := self.mesh(svo_name, self.resources[tree["svo"]][1], tree["textures"], (shape,))) is None:
                    continue
                child = {"name": f"{b['name']} shape", "mesh": m, "matrix": _row_major(f_floats(objs[shape]["_meshBindMatrix"]))}
                if child["matrix"] == IDENTITY:
                    del child["matrix"]
                g["nodes"].append(child)
                g["nodes"][first + i].setdefault("children", []).append(len(g["nodes"]) - 1)
        by_name = {b["name"]: (first + i, b) for i, b in enumerate(bones)}
        tracks = {by_name[n][0]: sample_motion(m, frames, by_name[n][1]["rotation"]) for n, m in nodes.items() if n in by_name}
        self.motions.append((f"motion {self.resources[tree['motion']][0]}", frames, tracks, tree["rate"]))
        return [first + i for i, b in enumerate(bones) if b["parent"] is None]

    def primitive_node(self, tree: dict, prim: dict) -> int | None:
        """SglPrimitive as a centred w x h quad in the XY plane (unlit, alpha blended), placed by its own matrix.
        A flipbook that switches images gets the whole texture list as extras.images."""
        g, res = self.glb.gltf, self.resources
        names = [res[t][0] for t in prim["textures"] if 0 <= t < len(res)]
        texs = [self.texture(res[t][0], res[t][1]) for t in prim["textures"] if 0 <= t < len(res)]
        if not texs or texs[0] is None:
            return None
        key = ("primitive", prim["width"], prim["height"], names[0], tuple(prim["color"]), "screen" in prim)
        if key not in self.meshes:
            w, h = prim["width"] / 2, prim["height"] / 2
            pos = struct.pack("<12f", -w, h, 0, w, h, 0, w, -h, 0, -w, -h, 0)
            g = self.glb.gltf
            attrs = {"POSITION": self.glb.accessor(pos, 5126, 4, "VEC3", 34962, min=[-w, -h, 0], max=[w, h, 0]),
                     "NORMAL": self.glb.accessor(struct.pack("<12f", *[0, 0, 1] * 4), 5126, 4, "VEC3", 34962),
                     "TEXCOORD_0": self.glb.accessor(struct.pack("<8f", 0, 0, 1, 0, 1, 1, 0, 1), 5126, 4, "VEC2", 34962)}
            idx = self.glb.accessor(struct.pack("<6H", 0, 3, 2, 0, 2, 1), 5123, 6, "SCALAR", 34963)
            mat = {"name": names[0], "doubleSided": True, "alphaMode": "BLEND",
                   "pbrMetallicRoughness": {"baseColorTexture": {"index": texs[0]}, "baseColorFactor": prim["color"],
                                            "metallicFactor": 0, "roughnessFactor": 1},
                   "extensions": {"KHR_materials_unlit": {}}}
            used = g.setdefault("extensionsUsed", [])
            if "KHR_materials_unlit" not in used:
                used.append("KHR_materials_unlit")
            g["materials"].append(mat)
            g["meshes"].append({"name": names[0], "primitives": [{"attributes": attrs, "indices": idx, "material": len(g["materials"]) - 1}]})
            self.meshes[key] = len(g["meshes"]) - 1
        node = {"name": f"primitive {names[0]}", "mesh": self.meshes[key]}
        if tree["matrix"] != IDENTITY:  # SglPrimitive isn't a propagating type: its matrix places the quad itself
            node["matrix"] = tree["matrix"]
        if any(u["kind"] == "flip" and (u["randomImage"] or u["images"][1] > u["images"][0]) for u in tree.get("uv", [])):
            node["extras"] = {"images": [t for t in texs if t is not None]}
        if "screen" in prim:  # Sgl2DPrimitive: the viewer draws it over the background in screen pixels
            node.setdefault("extras", {})["screen"] = prim["screen"]
        g["nodes"].append(node)
        return len(g["nodes"]) - 1

    def write_clip(self, name: str, tracks: dict[int, list[tuple]], rate: float = 1.0) -> None:
        """One glTF animation from per-frame (translation, rotation, scale) samples keyed by glTF node; `rate`
        frames of the samples pass per 60 fps frame."""
        from chuni.stage3d.anim import FPS, reduce_keys
        g = self.glb.gltf
        anim = {"name": name, "channels": [], "samplers": []}
        for index, trs in tracks.items():
            trs = list(trs)
            for i in range(1, len(trs)):  # keep quaternions on one hemisphere so slerp takes the short way
                if sum(a * b for a, b in zip(trs[i][1], trs[i - 1][1])) < 0:
                    trs[i] = (trs[i][0], [-v for v in trs[i][1]], trs[i][2])
            node = g["nodes"][index]
            node.pop("matrix", None)
            node["translation"], node["rotation"], node["scale"] = (list(v) for v in trs[0])
            for slot, path, width in ((0, "translation", "VEC3"), (1, "rotation", "VEC4"), (2, "scale", "VEC3")):
                values = [list(t[slot]) for t in trs]
                if all(v == values[0] for v in values):
                    continue
                keep = reduce_keys(values)
                times = [k / FPS / rate for k in keep]
                flat = [x for k in keep for x in values[k]]
                t_acc = self.glb.accessor(struct.pack(f"<{len(times)}f", *times), 5126, len(times), "SCALAR",
                                          None, min=[times[0]], max=[times[-1]])
                v_acc = self.glb.accessor(struct.pack(f"<{len(flat)}f", *flat), 5126, len(keep), width, None)
                anim["samplers"].append({"input": t_acc, "output": v_acc, "interpolation": "LINEAR"})
                anim["channels"].append({"sampler": len(anim["samplers"]) - 1, "target": {"node": index, "path": path}})
        if anim["channels"]:
            g.setdefault("animations", []).append(anim)

    def animate(self, clips: list) -> None:
        """glTF animations from stage_anim.sample() plus the baked .uvc motions."""
        from chuni.stage3d.anim import decompose
        for name, frames, tracks in clips:
            self.write_clip(name, {self.node_ids[t]: [decompose(m) for m in track]
                                   for t, track in tracks.items() if t in self.node_ids})
        for name, frames, tracks, rate in self.motions:
            self.write_clip(name, tracks, rate)


def export_stage(afb_path: str, glb_path: str) -> int:
    """Writes the .glb and returns the number of models in it (no file when 0)."""
    afnc, ptrs, resources = read_afb(afb_path)
    exporter = _StageExporter(resources)
    tree = scene_tree(afnc, ptrs)
    roots = exporter.glb.gltf["scenes"][0]["nodes"]
    if (root := exporter.node(tree)) is not None:
        roots.append(root)
    from chuni.stage3d.anim import sample
    exporter.animate(sample(tree))
    # svo resources no scene node references still get exported, at their file position
    placed = {m["svo"] for m in scene_models(tree)}
    for i, (name, data) in enumerate(resources):
        if name.lower().endswith(".svo") and i not in placed and (mesh := exporter.mesh(name, data, {})) is not None:
            exporter.glb.gltf["nodes"].append({"name": name, "mesh": mesh})
            roots.append(len(exporter.glb.gltf["nodes"]) - 1)
    count = sum("mesh" in n for n in exporter.glb.gltf["nodes"])  # a camera alone isn't worth a file
    if count:  # some lanes are texture-only (no model), nothing to write
        exporter.glb.write(glb_path)
    return count


if __name__ == "__main__":
    import sys
    m = _mul(_translate(1, 2, 3), _rotate(0, 0, 90))  # rotate first, then translate
    assert [round(v, 6) for v in m[:3] + m[12:15]] == [0, 1, 0, 1, 2, 3]
    look = _look_at((0, 0, 10), (0, 0, 0))  # from +z towards the origin: no rotation
    assert [round(v, 6) for v in look] == [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 10, 1]
    for path in sys.argv[1:-1]:
        out = os.path.join(sys.argv[-1], os.path.splitext(os.path.basename(path))[0] + ".glb")
        afnc, ptrs, resources = read_afb(path)
        models = scene_models(scene_tree(afnc, ptrs))
        for m in models:
            assert 0 <= m["svo"] < len(resources) and resources[m["svo"]][0].endswith(".svo"), m
            assert all(resources[i][0].endswith(".dds") for i in m["textures"].values()), m
        print(os.path.basename(path), len(models), "model nodes ->", export_stage(path, out), "meshes placed")
