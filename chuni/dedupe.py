"""Delete files identical to the same path in the previous version that has it.

    uv run python -m chuni.dedupe ~/storage.chuni.best/chuni [--apply]

Dry run unless --apply. Serving side must fall back to older versions on a miss;
the nginx snippet is printed at the end. Re-run after every regenerate of the mirror.
"""
import hashlib
import sys
from pathlib import Path


def digest(p: Path) -> bytes:
    return hashlib.sha1(p.read_bytes()).digest()


def dedupe(root: Path, apply: bool) -> list[str]:
    versions = sorted(p.name for p in root.iterdir() if p.is_dir() and p.name.isdigit())
    latest: dict[str, bytes] = {}  # rel path -> hash of newest version that still holds it
    for v in versions:
        saved = n = 0
        for p in sorted((root / v).rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root / v).as_posix()
            h = digest(p)
            if latest.get(rel) == h:
                saved += p.stat().st_size
                n += 1
                if apply:
                    p.unlink()
            else:
                latest[rel] = h
        if apply:  # drop dirs emptied above
            for d in sorted((root / v).rglob("*"), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
        print(f"{v}: {'removed' if apply else 'would remove'} {n} files, {saved >> 20} MiB")
    return versions


def nginx(versions: list[str]) -> str:
    out = ["# inside the server block; root must be the dir holding chuni/"]
    for i, v in enumerate(versions):
        chain = " ".join(f"/chuni/{o}/$1" for o in reversed(versions[: i + 1]))
        out.append(f"location ~ ^/chuni/{v}/(.+)$ {{ try_files {chain} =404; }}")
    return "\n".join(out)


if __name__ == "__main__":
    vs = dedupe(Path(sys.argv[1]).expanduser(), "--apply" in sys.argv)
    print(nginx(vs))
