import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_bool, get_int, get_text_element, get_version


def parse_frame(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "sortName": get_text_element(root, "sortName"),
        "defaultHave": get_bool(root, "defaultHave"),
        "explainText": get_text_element(root, "explainText"),
        "priority": get_int(root, "priority"),
        "imageFile": get_text_element(root, "image/path"),
    }

def copy_frame_image(input: str, frame: dict, output: str) -> None:
    img = Image.open(os.path.join(input, frame["imageFile"]))
    frame["image"] = f"{os.path.splitext(frame['imageFile'])[0]}.webp"
    img.save(os.path.join(output, frame["image"]))
