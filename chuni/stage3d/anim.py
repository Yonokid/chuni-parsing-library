"""Simulate the AFNC motion modules of a stage and sample one loop of node transforms."""
import math
import random
import struct

from chuni.stage3d.export import IDENTITY, PROPAGATES, _matrix_key, _mul, _rotate, _scale, _translate

FPS = 60
MAX_FRAMES = 36000  # cap the baked loop at 10 minutes


def _ease(kind: int, x: float, power: float) -> float:
    if kind == 1:
        return math.sin(x * math.pi / 2)
    if kind == 2:
        return 1 + math.sin(x * math.pi / 2 - math.pi / 2)
    if kind in (3, 5):
        return x ** power if power > 0 else x
    if kind == 4:
        return x ** (1 / power) if power > 0 else x
    return x


def _mid(a: float, b: float) -> float:
    return (a + b) / 2 if b >= 0 else a


def _keys_matrix(keys: list[tuple], t: float) -> list[float]:
    m = IDENTITY
    for key in keys:
        mode, target, start = key[0], key[1], key[6]
        if mode in (1, 5) and t >= start:  # velocity: A (or the middle of A..B) per frame since start
            v = key[13:16] if mode == 1 else [(p + q) / 2 for p, q in zip(key[13:16], key[17:20])]
            v = [x * (t - start) for x in v]
            op = _translate(*v) if target == 0 else _rotate(*v) if target == 1 else \
                _scale(*(1 + x for x in v)) if target == 2 else None
        elif mode in (3, 7) and t >= start:
            v = _oscillate(key, t)
            op = _translate(*v) if target == 0 else _rotate(*v) if target == 1 else _scale(*v) if target == 2 else None
        else:
            op = _matrix_key(key)
        if op:
            m = _mul(m, op)
    return m


def _pick(a: float, b: float, rng) -> float:
    return a + (b - a) * rng.random() if b >= 0 else a


def _resolve(key: tuple, rng) -> tuple:
    """Rolls a random key (modes 4/5/7) into its fixed counterpart (0/1/3); [5] set = one roll for all axes."""
    mode, k = key[0], list(key)
    if mode in (4, 5):
        u = rng.random()
        k[13:16] = [a + (b - a) * (u if key[5] else rng.random()) for a, b in zip(key[13:16], key[17:20])]
        k[0] = mode - 4
    elif mode == 7:
        k[0], k[9], k[11] = 3, _pick(key[9], key[10], rng), _pick(key[11], key[12], rng)
        for lo, hi in ((13, 17), (21, 25)):
            u = rng.random()
            k[lo:lo + 3] = [a + (b - a) * (u if key[5] else rng.random()) for a, b in zip(key[lo:lo + 3], key[hi:hi + 3])]
    return tuple(k)


def _rolled(mod: dict, rng) -> dict:
    """A module with its random values rolled, as the engine does each time a state is entered."""
    if mod["type"] == 100:
        return {**mod, "keys": [_resolve(k, rng) for k in mod["keys"]]}
    if mod["type"] == 106:
        entries = [{**e, "goal": [_pick(p, q, rng) for p, q in zip(e["goal"], e["alt"])] if e["random"] else e["goal"],
                    "random": 0, "duration": _pick(e["duration"], e["duration_max"], rng), "duration_max": -1.0}
                   for e in mod["entries"]]
        return {**mod, "entries": entries}
    return mod


def _period(key: tuple) -> float:
    return max(key[9] if key[0] == 3 else _mid(key[9], key[10]), 1e-7)


def _oscillate(key: tuple, t: float) -> list[float]:
    """Oscillation key value at module time t (MomMatrix update 0x1dca320; the engine's sine takes 65536ths of a turn).

    Swings between A [13..15] and B [21..23] (setup 0x1dc9ce0; [17..19]/[25..27] are their random partners)."""
    phase = key[11] if key[0] == 3 else _mid(key[11], key[12])
    s = math.sin(math.radians(360 * t / _period(key) + phase))
    return [(a + b) / 2 + (a - b) / 2 * s for a, b in zip(key[13:16], key[21:24])]


class _Goal:
    def __init__(self, mod: dict):
        self.mod, self.time, self.loops = mod, 0.0, mod["loops"]
        self.base, self.done = IDENTITY, False
        begin, self.schedule = 0.0, []
        for e in mod["entries"]:
            start = e["start"] if e["start"] >= 0 else begin
            duration = max(_mid(e["duration"], e["duration_max"]), 0.0)
            self.schedule.append((start, duration, e))
            begin = start + duration
        self.length = mod["total"] if mod["total"] >= 0 else begin

    def offset(self) -> list[float]:
        t, r, s = [0.0] * 3, [0.0] * 3, [1.0] * 3
        for start, duration, e in self.schedule:
            if self.time < start or e["interp"] != 0:
                continue
            x = 1.0 if duration <= 0 else min((self.time - start) / duration, 1.0)
            k = _ease(e["ease"], x, e["power"])
            goal = e["goal"] if not e["random"] else [(p + q) / 2 for p, q in zip(e["goal"], e["alt"])]
            cur = (t, r, s)[e["channel"]] if e["channel"] in (0, 1, 2) else None
            if cur is not None:
                for i in range(3):
                    cur[i] += (goal[i] - cur[i]) * k
        return _mul(_mul(_mul(self.base, _translate(*t)), _rotate(*r)), _scale(*s))

    def step(self, persist: list[float], dt: float = 1.0) -> list[float]:
        """Advance dt frames; returns the node's persistent matrix (updated when the module finishes)."""
        self.time += dt
        if self.time < self.length or self.length <= 0 and self.time < 1:
            return persist
        reached = self.offset()
        self.loops -= 1
        if self.mod["loops"] < 0 or self.loops >= 0:
            self.time = 0.0
            if self.mod["accumulate"]:
                self.base = reached
            return persist
        self.done = True  # out of loops: the reached offset stays
        return _mul(persist, reached)


class _Node:
    def __init__(self, tree: dict):
        self.tree, self.persist, self.state, self.rate = tree, IDENTITY, None, tree.get("rate", 1.0)
        self.rng = random.Random(f"{tree['type']}#{tree['index']}")  # seeded: re-exports stay byte-identical
        self.always = [_rolled(m, self.rng) for lane_id, mods in tree["lanes"] if lane_id == -1 for m in mods]
        self.goals = [_Goal(m) for m in self.always if m["type"] == 106]
        self.enter(0)

    def enter(self, state: int):
        self.state, self.time = state, 0.0
        self.active = [_rolled(m, self.rng) for lane_id, mods in self.tree["lanes"] if lane_id == state for m in mods]
        self.lane_goals = [_Goal(m) for m in self.active if m["type"] == 106]
        self.timers = [[m, 0.0, m["repeat"]] for m in self.active if m["type"] == 751]

    def matrix(self) -> list[float]:
        """Modules apply in list order onto the node matrix (MomMatrixGoal: node = node * goal, 0x1dccf60), so a
        goal listed before a scale key moves the node unscaled. Finished goals (persist) sit before the first goal."""
        m, persisted = IDENTITY, False
        goals = {id(g.mod): g for g in self.goals + self.lane_goals}
        for mod in self.always + self.active:
            if mod["type"] == 100 and mod["what"] == 0:
                m = _mul(m, _keys_matrix(mod["keys"], self.time if mod in self.active else self.clock))
            elif mod["type"] == 106:
                if not persisted:
                    m, persisted = _mul(m, self.persist), True
                if not goals[id(mod)].done:
                    m = _mul(m, goals[id(mod)].offset())
        return m if persisted else _mul(m, self.persist)

    def step(self):
        for g in self.goals + self.lane_goals:
            if not g.done:
                self.persist = g.step(self.persist, self.rate)
        for timer in self.timers:
            mod, waited, left = timer
            if left == 0 or mod["condition"] != 0:
                continue
            if waited >= mod["value"]:
                timer[2] -= 1
                for kind, target, _, arg, value, rand, _ in mod["actions"]:
                    if kind == 2 and target in (3, 5):
                        self.enter(value if rand < 0 else self.rng.randint(min(value, rand), max(value, rand)))
                        return
            timer[1] += self.rate
        self.time += self.rate


def _kinds(tree: dict) -> set[str]:
    kinds = set()
    for _, mods in tree["lanes"]:
        for m in mods:
            if m["type"] in (106, 751):
                kinds.add("scene")
            elif m["type"] == 100 and m["what"] == 0 and any(k[0] in (1, 3, 5, 7) for k in m["keys"]):
                kinds.add("spin")
    return kinds


def _spin_frames(tree: dict) -> int:
    """One full turn of every rotating velocity key (lcm of 360 / speed) and oscillation period; 0 when it only
    drifts."""
    period = 0
    for _, mods in tree["lanes"]:
        for m in mods:
            for k in m.get("keys", []) if m["type"] == 100 else []:
                if k[0] in (3, 7):
                    turn = max(int(round(_period(k))), 1)
                    period = math.lcm(period or turn, turn)
                    continue
                if k[0] not in (1, 5):
                    continue
                if k[1] != 1:
                    return 0  # constant drift never loops
                v = k[13:16] if k[0] == 1 else [(p + q) / 2 for p, q in zip(k[13:16], k[17:20])]
                for speed in v:
                    if abs(speed) > 1e-6:
                        turn = int(round(360 / abs(speed)))
                        period = math.lcm(period or turn, turn)
    return min(int(round(period / tree.get("rate", 1.0))), MAX_FRAMES)


def _state_cycle(tree: dict) -> int:
    """Length of the repeating part of a node's state machine (0 if it settles), following timer changes."""
    lanes = {}
    for lane_id, mods in tree["lanes"]:
        lanes.setdefault(lane_id, []).extend(mods)
    state, time, entered = 0, 0, {}
    while state not in entered and len(entered) < 64:
        entered[state] = time
        changes = [(m["value"], a[4]) for m in lanes.get(state, []) if m["type"] == 751 and m["condition"] == 0
                   for a in m["actions"] if a[0] == 2 and a[1] in (3, 5)]
        if not changes:
            return 0
        wait, state = min(changes)
        time += wait
    return time - entered.get(state, time)


def loop_frames(nodes: list[dict]) -> int:
    """Shortest loop after which every state cycle and endless goal lines up (lcm of their lengths)."""
    period = 0
    for tree in nodes:
        lengths = [_state_cycle(tree)]
        lengths += [_Goal(m).length for lane_id, mods in tree["lanes"] if lane_id == -1 for m in mods
                    if m["type"] == 106 and m["loops"] < 0]
        lengths += [_period(k) for _, mods in tree["lanes"] for m in mods if m["type"] == 100 and m["what"] == 0
                    for k in m["keys"] if k[0] in (3, 7)]
        for length in lengths:
            length /= tree.get("rate", 1.0)
            if length >= 1:
                period = math.lcm(period or int(round(length)), int(round(length)))
    if not period:  # nothing repeats: bake the longest one-shot goal (Future village: the planet turns 240° in 3 min)
        once = [_Goal(m).length * (m["loops"] + 1) / t.get("rate", 1.0) for t in nodes for lane_id, mods in t["lanes"]
                if lane_id == -1 for m in mods if m["type"] == 106 and m["loops"] >= 0]
        period = int(round(max(once, default=0)))
    return min(period, MAX_FRAMES)


def _track(tree: dict, frames: int) -> list[list[float]]:
    node, track = _Node(tree), []
    node.clock = 0.0
    for _ in range(frames + 1):
        track.append(node.matrix())
        node.step()
        node.clock += node.rate
    return track


def sample(tree: dict) -> list[tuple[str, int, dict[int, list[list[float]]]]]:
    """Animation clips as (name, length in frames, {id(tree node): local matrix per frame}).

    Nodes driven by goals/states share one "scene" clip whose length lines up every cycle (so the stage camera
    and the objects it passes loop together); pure spinners get one clip each, one turn long.
    """
    scene, spinners, stack = [], [], [tree]
    while stack:
        t = stack.pop()
        stack += t["children"]
        if t["type"] not in PROPAGATES:
            continue
        kinds = _kinds(t)
        if "scene" in kinds:
            scene.append(t)
        elif "spin" in kinds:
            spinners.append(t)
    clips = []
    frames = loop_frames(scene) if scene else 0
    if frames and frames < MAX_FRAMES:
        clips.append(("scene", frames, {id(t): _track(t, frames) for t in scene}))
    else:  # cycles don't line up (independent props): loop each node on its own cycle
        for t in scene:
            if f := loop_frames([t]):
                clips.append((f"loop {t['type']}#{t['index']}", f, {id(t): _track(t, f)}))
    for t in spinners:
        if frames := _spin_frames(t):
            clips.append((f"spin {t['type']}#{t['index']}", frames, {id(t): _track(t, frames)}))
    return clips


def _hermite(keys: list[tuple[int, float, float]], t: float) -> float:
    """Cubic Hermite through (frame, value, tangent per frame) keys; clamps outside the first/last key."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (f0, v0, m0), (f1, v1, m1) in zip(keys, keys[1:]):
        if t <= f1:
            h = f1 - f0
            if h <= 0:
                return v1
            x = (t - f0) / h
            return ((2 * x ** 3 - 3 * x ** 2 + 1) * v0 + (x ** 3 - 2 * x ** 2 + x) * h * m0
                    + (-2 * x ** 3 + 3 * x ** 2) * v1 + (x ** 3 - x ** 2) * h * m1)
    return keys[-1][1]


def motion(uvc: bytes) -> tuple[int, dict[str, dict]]:
    """Transform animation of a .uvc"""
    from chuni.stage3d.yabx import avts, f_int, read_yabx
    pools = {kind: data for kind, data in avts(uvc).values()}
    prop = next(o for o in read_yabx(pools[0]) if o["_class"] == "uva::SceneProperty")
    frames, nodes = f_int(prop["_frameNumber"]), pools.get(1, b"")
    if not nodes:
        return frames, {}
    names = pools.get(6, b"").split(b"\0")
    count = struct.unpack_from("<I", nodes)[0]
    stride = (len(nodes) - 4) // count if count else 0

    def curve(kind: int, first: int, n: int):
        pool = pools.get({0: 2, 1: 3, 2: 4}[kind], b"")  # kind 3 (1.20.00+: pool 5, one int16 per frame, scale unknown) is skipped by the caller
        if kind == 2:
            values = struct.unpack_from(f"<{n}f", pool, 4 + 4 * first)
            return [(i, v, 0.0) for i, v in enumerate(values)]
        if kind == 0:
            return [(f & 0xFFFF, v, m) for v, m, f in (struct.unpack_from("<ffI", pool, 4 + 12 * (first + i)) for i in range(n))]
        return [(f & 0x7FFF, v / 32767, m) for m, v, f in (struct.unpack_from("<fhH", pool, 4 + 8 * (first + i)) for i in range(n))]

    out = {}
    for i in range(count):
        o = 4 + stride * i
        ints, floats = struct.unpack_from("<43i", nodes, o), struct.unpack_from("<43f", nodes, o)
        curves = {slot: curve(*ints[slot * 3:slot * 3 + 3]) for slot in range(11) if ints[slot * 3 + 2] > 0 and ints[slot * 3] in (0, 1, 2)}
        if curves and i < len(names):
            out[names[i].decode("utf-8", "replace")] = {"curves": curves, "translation": floats[37:40], "scale": floats[40:43]}
    return frames, out


def uv_motion(uvc: bytes) -> dict | None:
    """UV offset animation of a .uvc (pool kind 9: u32 count, 68-byte records whose first slots are
    {type, first key, count} channels for the U and V offset; keys in the shared pools). Returns a looping
    {"kind": "keys", "set": 0, "loop": True, "keys": [[seconds, u, v], ...]} UV module, or None."""
    from chuni.stage3d.yabx import avts, f_int, read_yabx
    pools = {kind: data for kind, data in avts(uvc).values()}
    table = pools.get(9, b"")
    if len(table) < 4 or not struct.unpack_from("<I", table)[0]:
        return None
    prop = next(o for o in read_yabx(pools[0]) if o["_class"] == "uva::SceneProperty")
    frames = f_int(prop["_frameNumber"])
    ints = struct.unpack_from("<6i", table, 4)
    curves = {}
    for axis in range(2):
        kind, first, n = ints[axis * 3:axis * 3 + 3]
        if n <= 0:
            continue
        pool = pools.get({0: 2, 1: 3, 2: 4}[kind], b"")  # kind 3 (1.20.00+: pool 5, one int16 per frame, scale unknown) is skipped by the caller
        if kind == 2:
            curves[axis] = [(i, v, 0.0) for i, v in enumerate(struct.unpack_from(f"<{n}f", pool, 4 + 4 * first))]
        elif kind == 0:
            curves[axis] = [(f & 0xFFFF, v, m) for v, m, f in (struct.unpack_from("<ffI", pool, 4 + 12 * (first + i)) for i in range(n))]
        else:
            curves[axis] = [(f & 0x7FFF, v / 32767, m) for m, v, f in (struct.unpack_from("<fhH", pool, 4 + 8 * (first + i)) for i in range(n))]
    if not curves or frames <= 0:
        return None
    values = [[_hermite(curves[a], f) if a in curves else 0.0 for a in range(2)] for f in range(frames + 1)]
    return {"kind": "keys", "set": 0, "loop": True,
            "keys": [[k / FPS] + values[k] for k in reduce_keys(values)]}


def sample_motion(node: dict, frames: int, rest_rotation: list[float]) -> list[tuple]:
    """Per-frame (translation, rotation xyzw, scale) of one .uvc node, frames 0..frames inclusive."""
    curves, out = node["curves"], []
    for f in range(frames + 1):
        t = [_hermite(curves[k], f) if k in curves else node["translation"][k] for k in range(3)]
        s = [_hermite(curves[3 + k], f) if 3 + k in curves else node["scale"][k] for k in range(3)]
        if 10 in curves and _hermite(curves[10], f) < 0.5:  # hidden: glTF has no visibility, collapse instead
            s = [1e-6] * 3
        if any(6 + k in curves for k in range(4)):
            q = [_hermite(curves[6 + k], f) if 6 + k in curves else (1.0 if k == 3 else 0.0) for k in range(4)]
            n = math.sqrt(sum(v * v for v in q)) or 1
            q = [v / n for v in q]
        else:
            q = list(rest_rotation)
        out.append((t, q, s))
    return out


def decompose(m: list[float]) -> tuple[list[float], list[float], list[float]]:
    """Column-major TRS matrix -> (translation, rotation quaternion xyzw, scale)."""
    cols = [m[0:3], m[4:7], m[8:11]]
    scale = [math.sqrt(sum(v * v for v in c)) or 1e-6 for c in cols]
    det = (cols[0][0] * (cols[1][1] * cols[2][2] - cols[2][1] * cols[1][2])
           - cols[1][0] * (cols[0][1] * cols[2][2] - cols[2][1] * cols[0][2])
           + cols[2][0] * (cols[0][1] * cols[1][2] - cols[1][1] * cols[0][2]))
    if det < 0:
        scale[0] = -scale[0]
    r = [[cols[c][row] / scale[c] for c in range(3)] for row in range(3)]  # r[row][col]
    tr = r[0][0] + r[1][1] + r[2][2]
    if tr > 0:
        w = math.sqrt(1 + tr) * 2
        q = [(r[2][1] - r[1][2]) / w, (r[0][2] - r[2][0]) / w, (r[1][0] - r[0][1]) / w, w / 4]
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        w = math.sqrt(1 + r[0][0] - r[1][1] - r[2][2]) * 2
        q = [w / 4, (r[0][1] + r[1][0]) / w, (r[0][2] + r[2][0]) / w, (r[2][1] - r[1][2]) / w]
    elif r[1][1] > r[2][2]:
        w = math.sqrt(1 + r[1][1] - r[0][0] - r[2][2]) * 2
        q = [(r[0][1] + r[1][0]) / w, w / 4, (r[1][2] + r[2][1]) / w, (r[0][2] - r[2][0]) / w]
    else:
        w = math.sqrt(1 + r[2][2] - r[0][0] - r[1][1]) * 2
        q = [(r[0][2] + r[2][0]) / w, (r[1][2] + r[2][1]) / w, w / 4, (r[1][0] - r[0][1]) / w]
    n = math.sqrt(sum(v * v for v in q)) or 1
    return list(m[12:15]), [v / n for v in q], scale


def reduce_keys(values: list[list[float]], eps: float = 1e-4) -> list[int]:
    """Frame indices to keep so linear interpolation reproduces the samples (keeps both sides of jumps).

    Douglas-Peucker: split each span at its worst sample until every sample is within eps (relative above 1)."""
    keep, spans = {0, len(values) - 1}, [(0, len(values) - 1)]
    while spans:
        s, e = spans.pop()
        a, c, worst, at = values[s], values[e], eps, -1
        for i in range(s + 1, e):
            f, b = (i - s) / (e - s), values[i]
            err = max(abs(a[k] + (c[k] - a[k]) * f - b[k]) / max(1.0, abs(b[k])) for k in range(len(b)))
            if err > worst:
                worst, at = err, i
        if at >= 0:
            keep.add(at)
            spans += [(s, at), (at, e)]
    return sorted(keep)


if __name__ == "__main__":
    import sys
    from chuni.stage3d.export import read_afb, scene_tree
    assert _ease(0, 0.5, 1) == 0.5 and abs(_ease(1, 1.0, 1) - 1) < 1e-9
    t, q, s = decompose(_mul(_translate(1, 2, 3), _rotate(0, 90, 0)))
    assert [round(v, 6) for v in t + s] == [1, 2, 3, 1, 1, 1] and abs(abs(q[1]) - math.sqrt(0.5)) < 1e-6
    assert reduce_keys([[0], [1], [2], [2], [2], [9]]) in ([0, 2, 4, 5], [0, 1, 2, 4, 5])
    slow = [[math.sin(f / 1600 * 2 * math.pi) * 0.03] for f in range(14401)]  # a gentle sway must not flatten
    assert len(reduce_keys(slow)) > 20
    uniform = (4, 2, 0, 0, 0, 1) + (0.0,) * 7 + (1.2, 1.2, 1.2, 0.0, 0.5, 0.5, 0.5)  # random scale, one roll
    k = _resolve(uniform, random.Random(1))
    assert k[0] == 0 and k[13] == k[14] == k[15] and 0.5 <= k[13] <= 1.2
    assert _hermite([(0, 0.0, 1.0), (10, 10.0, 1.0)], 5) == 5.0 and _hermite([(0, 1.0, 0.0)], 9) == 1.0
    osc = (3, 0, 0, 0, 0, 0, 0.0, -1.0, 1, 100.0, 60.0, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 9.0, 9.0, 9.0, 0.0) + (0.0,) * 8
    assert _oscillate(osc, 0) == [10, 0, 0] and [round(v, 6) for v in _oscillate(osc, 25)] == [20, 0, 0]
    sway = osc[:13] + (0.0, 3.5, 0.0) + (0.0,) * 5 + (0.0, -3.5, 0.0) + (0.0,) * 5  # Yellow Ring's tunnel sway
    assert _oscillate(sway, 0) == [0, 0, 0] and [round(v, 6) for v in _oscillate(sway, 75)] == [0, -3.5, 0]
    for path in sys.argv[1:]:
        clips = sample(scene_tree(*read_afb(path)[:2]))
        print(path.rsplit("/", 1)[-1], [(name, frames, len(tracks)) for name, frames, tracks in clips])
