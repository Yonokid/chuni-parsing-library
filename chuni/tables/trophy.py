import xml.etree.ElementTree as ET

from chuni.utils import (get_int, get_text_element, parse_conditions,
                          parse_open_condition, safe_find)


def parse_trophy(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["explainText"] = get_text_element(root, "explainText")
        json_data["rareType"] = int(get_text_element(root, "rareType"))
        json_data["defaultHave"] = get_text_element(root, "defaultHave") == "true"
        json_data["priority"] = get_int(root, "priority")
        json_data["openCondition"] = parse_open_condition(safe_find(root, "openCondition"))
        json_data["conditions"] = parse_conditions(root)

    return json_data
