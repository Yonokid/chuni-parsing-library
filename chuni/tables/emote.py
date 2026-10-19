import json
import os
import xml.etree.ElementTree as ET

from chuni.emote.psb import export_emote
from chuni.utils import get_int, get_text_element, get_version


NAMES = {"yuni": "uni"}  # the file names misspell the character's name
TITLES = {"uni": "Uni", "navi": "Navi", "exyear": "Ixia"}


def _header(root: ET.Element) -> dict:
    return {"id": get_int(root, "name/id"), "version": get_version(root), "name": get_text_element(root, "name/str")}


def parse_emoteChara(file: str) -> dict:
    root = ET.parse(file).getroot()
    json_data = {**_header(root), **{k: get_int(root, k) for k in ("emoteDataId", "texSizeX", "texSizeY", "posX", "posY", "scaleX10000")}}
    if root.find("dialogName") is not None:  # 2.45+: speaker name shown in the dialog
        json_data["dialogName"] = get_text_element(root, "dialogName")
    return json_data


def parse_emoteScene(file: str) -> dict:
    root = ET.parse(file).getroot()
    return {**_header(root), "emoteChara": [get_int(root, "emoteChara0"), get_int(root, "emoteChara1")],
            **{k: get_int(root, k) for k in ("emoteCharaPos", "emoteScriptStart", "emoteScriptEnd")}}


def parse_emoteScript(file: str) -> dict:
    root = ET.parse(file).getroot()
    json_data = {**_header(root), "msecNext": get_int(root, "msecNext")}
    # 8 timeline slots, each a (main, diff) pair for emote chara 0 and 1; id 0 means unset
    json_data["timelines"] = [{
        "offset": get_int(root, f"emoteTimeline{i}Offset"),
        "main": [get_int(root, f"emoteTimeline{i}MainId{c}") for c in (0, 1)],
        "diff": [get_int(root, f"emoteTimeline{i}DiffId{c}") for c in (0, 1)],
    } for i in range(8)]
    for key in ("msecDelay", "cue", "emoteScriptOffset", "emoteScriptButton", "isChangeDialog", "dialogCharaId"):
        if root.find(key) is not None:
            json_data[key] = get_int(root, key)
    if root.find("textDialog") is not None:
        json_data["textDialog"] = get_text_element(root, "textDialog")
    return json_data


def _parse_timeline(file: str) -> dict:
    root = ET.parse(file).getroot()
    return {**_header(root), "timeline": get_text_element(root, "timeline"), "timelineId": get_int(root, "timelineId")}


parse_emoteTimelineMain = parse_emoteTimelineDiff = _parse_timeline


def process_emotedata(directory: str, output_dir: str) -> None:
    """emotedata/emotedataNNNN/<chara>_res..._<tex>.emtbytes: unpack each E-mote PSB to JSON + atlas webp.

    Output emotedata/emotedata.json lists {id, name, title, file, textures}; file is <name>.json, textures are the atlas
    webps its sources point at (<name>.webp, or <name>_<n>.webp for models with several atlases).
    """
    src = os.path.join(directory, "emotedata")
    if not os.path.isdir(src):
        return
    out = os.path.join(output_dir, "emotedata")
    os.makedirs(out, exist_ok=True)
    entries = []
    for folder in sorted(os.listdir(src)):
        for f in sorted(os.listdir(os.path.join(src, folder))):
            if not f.endswith(".emtbytes"):
                continue
            name = f.split("_")[0]
            name = NAMES.get(name, name)
            try:
                root = export_emote(os.path.join(src, folder, f), out, name)
            except (ValueError, IndexError, KeyError) as e:
                print(f"Error processing emotedata {folder}/{f}: {e}")
                continue
            textures = [s["texture"]["pixel"] for s in root["source"].values() if isinstance(s, dict) and isinstance(s.get("texture", {}).get("pixel"), str)]
            entries.append({"id": int(folder.removeprefix("emotedata")), "name": name, "title": TITLES.get(name, name.title()), "file": f"{name}.json", "textures": textures})
    # later Options override earlier ones
    path = os.path.join(out, "emotedata.json")
    old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    merged = {e["id"]: e for e in old + entries}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sorted(merged.values(), key=lambda e: e["id"]), fh, indent=4, ensure_ascii=False)
