import os
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image

from libs.global_utils import get_text_element, safe_find


def parse_music(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = get_text_element(root, "name/id")
        json_data["version"] = get_text_element(root, "resourceVersion/str")
        json_data["name"] = get_text_element(root, "name/str")
        json_data["sortName"] = get_text_element(root, "sortName")
        json_data["artistName"] = get_text_element(root, "artistName/str")
        json_data["genreName"] = get_text_element(root, "genreNames/list/StringID/str")
        json_data["previewStartTime"] = int(get_text_element(root, "previewStartTime"))
        json_data["previewEndTime"] = int(get_text_element(root, "previewEndTime"))
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
            json_data["charts"].append(fumen_element)

    return json_data

def copy_cueFile(input: str, song: dict, output: str) -> None:
    id = f'music{song["id"].zfill(4)}'
    subprocess.run(["vgmstream/vgmstream-cli.exe", f"{input}\\{id}.awb", "-o", f"{input}\\{id}.wav"])
    subprocess.run(["ffmpeg", "-y", "-i", f"{input}\\{id}.wav", f"{output}\\{id}.mp3"])
    subprocess.run(["ffmpeg", "-y", "-i", f"{output}\\{id}.mp3",
                    "-ss", str(song["previewStartTime"]/1000), "-to", str(song["previewEndTime"]/1000),
                    f"{output}\\{id}_pre.mp3"])
    os.remove(f"{input}\\{id}.wav")

def copy_jacket(input: str, song: dict, output: str) -> None:
    img = Image.open(f"{input}\\CHU_UI_Jacket_{song["id"].zfill(4)}.dds")
    img.save(f"{output}\\CHU_UI_Jacket_{song["id"].zfill(4)}.webp")
