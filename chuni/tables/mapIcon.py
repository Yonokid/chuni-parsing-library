import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_bool, get_int, get_ref, get_text_element


def parse_mapIcon(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": int(get_text_element(root, "resourceVersion/str")),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "works": get_ref(root, "works"),
        "explainText": get_text_element(root, "explainText"),
        "defaultHave": get_bool(root, "defaultHave"),
        "priority": get_int(root, "priority"),
        "imageFile": get_text_element(root, "image/path"),
    }

def copy_mapIcon_image(input: str, icon: dict, output: str) -> None:
    img = Image.open(os.path.join(input, icon["imageFile"]))
    icon["image"] = f"{os.path.splitext(icon['imageFile'])[0]}.webp"
    img.save(os.path.join(output, icon["image"]))
