import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_ref, get_text_element, get_version


def parse_avatarAccessoryGacha(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "isDefault": get_bool(root, "isDefault"),
        "items": [
            {"avatarAccessory": get_ref(item, "avatarAccessoryName"), "weight": get_int(item, "weight")}
            for item in root.iter("AvatarAccessoryGachaItem")
        ],
    }
