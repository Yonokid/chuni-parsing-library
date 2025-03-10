import xml.etree.ElementTree as ET

from global_utils import get_text_element


def parse_present(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = get_text_element(root, "name/id")
        json_data["version"] = get_text_element(root, "resourceVersion/str")
        json_data["name"] = get_text_element(root, "name/str")
        json_data["messageText"] = get_text_element(root, "messageText")

    return json_data
