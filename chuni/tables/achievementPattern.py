import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_text_element, get_version


def parse_achievementPattern(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["disabled"] = get_bool(root, "disableFlag")
        json_data["explainText"] = get_text_element(root, "explainText")
        for key in ("patternType", "iconType", "unitType", "pos", "star", "priority"):
            json_data[key] = get_int(root, key)

    return json_data
