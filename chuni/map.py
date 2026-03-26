import os
import xml.etree.ElementTree as ET

from PIL import Image

from libs.global_utils import get_text_element


def parse_map(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = get_text_element(root, "name/id")
        json_data["version"] = get_text_element(root, "resourceVersion/str")
        json_data["name"] = get_text_element(root, "name/str")
        json_data["ddsMapId"] = get_text_element(root, "infos/MapDataAreaInfo/ddsMapName/id")

    return json_data

def copy_ddsMap(input: str, event: dict, output: str) -> None:
    files = os.listdir(input)
    dds_files = [f for f in files if f.endswith('.dds')]
    filename = os.path.splitext(dds_files[0])[0]
    img = Image.open(os.path.join(input, dds_files[0]))
    event["ddsMapName"] = f"{filename}.webp"
    img.save(os.path.join(output, f"{filename}.webp"))
