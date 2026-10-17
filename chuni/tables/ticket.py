import xml.etree.ElementTree as ET

from chuni.utils import get_text_element


def parse_ticket(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["type"] = int(get_text_element(root, "type"))
        json_data["stockMaxNum"] = int(get_text_element(root, "stockMaxNum"))
        json_data["explainText"] = get_text_element(root, "explainText")
        json_data["valueDay"] = int(get_text_element(root, "valueDay"))
        json_data["valueDayRaw"] = int(get_text_element(root, "valueDayRaw"))
        json_data["valueUse"] = int(get_text_element(root, "valueUse"))
        json_data["valueUseRaw"] = int(get_text_element(root, "valueUseRaw"))
        json_data["valueBoost"] = int(get_text_element(root, "valueBoost"))
        json_data["valueBoostRaw"] = int(get_text_element(root, "valueBoostRaw"))
        json_data["priority"] = int(get_text_element(root, "priority"))

    return json_data
