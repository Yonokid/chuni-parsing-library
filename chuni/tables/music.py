import os
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import (get_enum_name, get_int, get_ref, get_ref_list,
                          get_text_element, safe_find)


def parse_music(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["sortName"] = get_text_element(root, "sortName")
        json_data["artistName"] = get_text_element(root, "artistName/str")
        json_data["genreName"] = get_text_element(root, "genreNames/list/StringID/str")
        json_data["genres"] = get_ref_list(root, "genreNames/list")
        json_data["releaseTagName"] = get_text_element(root, "releaseTagName/str")
        json_data["exType"] = get_int(root, "exType")
        json_data["rightsInfo"] = get_ref(root, "rightsInfoName")
        json_data["musicLabel"] = get_enum_name(root, "musicLableID")
        json_data["jacketFile"] = get_text_element(root, "jaketFile/path")
        json_data["priority"] = get_int(root, "priority")
        json_data["cueFile"] = get_ref(root, "cueFileName")
        json_data["stage"] = get_ref(root, "stageName")
        json_data["previewStartTime"] = int(get_text_element(root, "previewStartTime"))
        json_data["previewEndTime"] = int(get_text_element(root, "previewEndTime"))
        json_data["firstLock"] = get_text_element(root, "firstLock") == "true"
        json_data["charts"] = []
        fumens = safe_find(root, "fumens")
        for fumen in fumens.iter("MusicFumenData"):
            fumen_element = dict()
            if (get_text_element(fumen, "enable")) == "false":
                continue
            fumen_element["difficulty"] = int(get_text_element(fumen, "type/id"))
            level = int(get_text_element(fumen, "level"))
            levelDecimal = int(get_text_element(fumen, "levelDecimal"))
            fumen_element["level"] = level + (levelDecimal/100)
            fumen_element["difficultyName"] = get_text_element(fumen, "type/data")  # str is the enum key (ID_00), data the label
            fumen_element["file"] = get_text_element(fumen, "file/path")
            fumen_element["notesDesigner"] = get_text_element(fumen, "notesDesigner")
            fumen_element["defaultBpm"] = get_int(fumen, "defaultBpm")
            if fumen_element["difficulty"] == 4:  # WORLD'S END: no level, a star rating and a kanji tag instead
                fumen_element["stars"] = get_int(root, "starDifType")
                fumen_element["worldsEndTag"] = get_text_element(root, "worldsEndTagName/str")
            json_data["charts"].append(fumen_element)

    return json_data

def copy_cueFile(input: str, song: dict, output: str) -> None:
    id = f'music{str(song["id"]).zfill(4)}'
    cue = f'music{str((song["cueFile"] or song)["id"]).zfill(4)}'  # WORLD'S END songs play another song's cue
    mp3, preview, wav = (os.path.join(output, f"{id}{suffix}") for suffix in (".mp3", "_pre.mp3", ".wav"))
    has_preview = song["previewEndTime"] > song["previewStartTime"]  # some songs ship 0-0
    if os.path.exists(mp3) and (os.path.exists(preview) or not has_preview):  # same song re-listed by a later Option
        return
    subprocess.run(["vgmstream-cli", os.path.join(input, f"{cue}.awb"), "-o", wav])  # wav goes in output: source dir may be a slow disk
    subprocess.run(["ffmpeg", "-y", "-i", wav, mp3])
    if has_preview:
        subprocess.run(["ffmpeg", "-y", "-i", mp3,
                        "-ss", str(song["previewStartTime"]/1000), "-to", str(song["previewEndTime"]/1000), preview])
    os.remove(wav)

def copy_jacket(input: str, song: dict, output: str) -> None:
    img = Image.open(os.path.join(input, song["jacketFile"]))
    img.save(os.path.join(output, f'CHU_UI_Jacket_{str(song["id"]).zfill(4)}.webp'))
