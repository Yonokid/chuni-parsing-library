import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_int, get_ref, get_text_element, safe_find


def parse_map(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["ddsMapId"] = get_text_element(root, "infos/MapDataAreaInfo/ddsMapName/id")
        json_data["mapType"] = get_int(root, "mapType")
        json_data["stopMapArea"] = get_ref(root, "stopMapAreaName")
        json_data["stopUnlockEvent"] = get_ref(root, "stopUnlockEventName")

        areas = []
        for info in safe_find(root, "infos").iter("MapDataAreaInfo"):
            area = {
                key: get_ref(info, f"{key}Name")
                for key in ("mapArea", "ddsMap", "music", "chara", "skill", "trophy", "normalGauge", "challengeGauge")
            }
            area["challengeRating"] = {
                dif: get_int(info, f"challengeRating/{dif}") for dif in ("advanced", "expert", "master")
            }
            areas.append(area)
        json_data["areas"] = areas

    return json_data

def copy_ddsMap(input: str, event: dict, output: str) -> None:
    files = os.listdir(input)
    dds_files = [f for f in files if f.endswith('.dds')]
    filename = os.path.splitext(dds_files[0])[0]
    img = Image.open(os.path.join(input, dds_files[0]))
    event["ddsMapName"] = f"{filename}.webp"
    img.save(os.path.join(output, f"{filename}.webp"))
