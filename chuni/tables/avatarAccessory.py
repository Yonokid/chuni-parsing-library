import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_bool, get_int, get_text_element, get_version


def parse_avatarAccessory(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "sortName": get_text_element(root, "sortName"),
        "category": get_int(root, "category"),
        "layerIndex": get_int(root, "layerIndex"),
        "defaultHave": get_bool(root, "defaultHave"),
        "explainText": get_text_element(root, "explainText"),
        "priority": get_int(root, "priority"),
        "imageFile": get_text_element(root, "image/path"),
        "textureFile": get_text_element(root, "texture/path"),
    }

def copy_avatarAccessory_image(input: str, item: dict, output: str) -> None:
    """Only the icon: the texture is a UV-mapped sheet for the 3D avatar."""
    img = Image.open(os.path.join(input, item["imageFile"]))
    item["image"] = f"{os.path.splitext(item['imageFile'])[0]}.webp"
    img.save(os.path.join(output, item["image"]))
