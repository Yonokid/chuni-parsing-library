import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_bool, get_int, get_text_element, get_version


def parse_namePlate(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        root = ET.parse(xml_file).getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["explainText"] = get_text_element(root, "explainText")
        json_data["defaultHave"] = get_bool(root, "defaultHave")
        json_data["priority"] = get_int(root, "priority")
        json_data["imageFile"] = get_text_element(root, "image/path")

    return json_data

def copy_namePlate_image(input: str, plate: dict, output: str) -> None:
    img = Image.open(os.path.join(input, plate["imageFile"]))
    plate["image"] = f"{os.path.splitext(plate['imageFile'])[0]}.webp"
    img.save(os.path.join(output, plate["image"]))
