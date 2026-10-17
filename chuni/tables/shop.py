import xml.etree.ElementTree as ET

from chuni.utils import (get_ref, get_text_element, parse_open_condition,
                          safe_find)


def parse_shop(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["closeFlag"] = get_text_element(root, "closeFlag") == "true"
        json_data["explainText"] = get_text_element(root, "explainText")
        json_data["price"] = int(get_text_element(root, "price"))
        json_data["saleCategoryName"] = get_text_element(root, "saleCategoryName/str")
        json_data["priority"] = int(get_text_element(root, "priority"))
        json_data["openCondition"] = parse_open_condition(safe_find(root, "openCondition"))

        substances = safe_find(root, "substances")
        json_data["substanceType"] = int(get_text_element(substances, "type"))
        for key in ("music", "ticket", "skill"):
            json_data[key] = get_ref(substances, f"{key}/name")

    return json_data
