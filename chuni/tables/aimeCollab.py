import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_int, get_ref, get_text_element, safe_find


def parse_aimeCollab(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["campaignId"] = get_int(root, "campaignID")
        json_data["imageFile"] = get_text_element(root, "image/path")
        json_data["substances"] = []
        for sub in safe_find(root, "substances/list").iter("AimeCollabSubstanceData"):
            json_data["substances"].append({
                "type": get_int(sub, "type"),
                "bitPos": get_int(sub, "bonus/bitPos"),
                "present": get_ref(sub, "bonus/presentName"),
            })

    return json_data

def copy_aimeCollab_image(input: str, collab: dict, output: str) -> None:
    img = Image.open(os.path.join(input, collab["imageFile"]))
    collab["image"] = f"{os.path.splitext(collab['imageFile'])[0]}.webp"
    img.save(os.path.join(output, collab["image"]))
