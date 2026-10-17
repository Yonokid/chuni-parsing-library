# chuni-parsing-library

Parses CHUNITHM / maimai DX game data into JSON and web-ready assets for [chuni-resource-viewer](https://github.com/Yonokid/chuni-resource-viewer).

## CHUNITHM

Run from the repo root:

```bash
uv run python -m chuni "<game>/App/data/A000" <output dir>   # base data
uv run python -m chuni "<game>/Option" <output dir>          # option folders (A001, A002, …), merged by id
uv run python -m chuni "<patch>/Option" <output dir> "<full game>/App/data/A000"  # when the version's own A000 is only a patch
```

Layout:

| Path | Contents |
|---|---|
| `chuni/parse.py` | the pipeline: runs every table parser and copies the related assets |
| `chuni/tables/` | one XML parser per data type (music, chara, stage, event, …) |
| `chuni/stage3d/` | 3D stages: `.afb` reader (`afb.py`), stevia object DB (`yabx.py`), `.glb` export (`export.py`), animation (`anim.py`) |
| `chuni/enums.py`, `chuni/sprites.py` | enum tables from `db/`, UI sprite sheets |
| `chuni/navigation.py` | writes `navigation.json` (viewer sidebar entries) for each output |
| `chuni/utils.py` | XML helpers |
| `tests/test_parsers.py` | smoke test: `uv run python -m tests.test_parsers "<game>/App/data/A000"` |

The 3D stage formats are documented in [docs/stage_formats.md](docs/stage_formats.md); remaining work is in [docs/stage_roadmap.md](docs/stage_roadmap.md).

## maimai DX

```bash
cd maimai && uv run python parse.py <data dir> <output dir>
```
