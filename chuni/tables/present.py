import xml.etree.ElementTree as ET

from chuni.utils import get_ref, get_text_element, get_version


def parse_present(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["messageText"] = get_text_element(root, "messageText")
        json_data["gamePoint"] = int(get_text_element(root, "gamePoint"))
        for key in ("ticket", "chara", "skill", "trophy"):
            json_data[f"{key}"] = get_ref(root, f"{key}Name")
        for key in ("skillSeed", "avatarAccessory", "frame", "symbolChat", "ultimaScore"):  # 2.00+ (ultimaScore 2.20+)
            if root.find(f"{key}Name") is not None:
                json_data[key] = get_ref(root, f"{key}Name")

    return json_data
