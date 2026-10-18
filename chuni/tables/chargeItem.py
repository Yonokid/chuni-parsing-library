import xml.etree.ElementTree as ET

from chuni.utils import get_text_element, get_version


def parse_chargeItem(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["type"] = int(get_text_element(root, "type"))
        json_data["expirationDays"] = int(get_text_element(root, "expirationDays"))
        json_data["itemNum"] = int(get_text_element(root, "itemNum"))
        json_data["consumeType"] = int(get_text_element(root, "consumeType"))
        json_data["forceUse"] = get_text_element(root, "forceUse") == "true"
        json_data["sellingAppeal"] = get_text_element(root, "sellingAppeal") == "true"
        # substances holds one child per type (only type 1, ticket, has been seen); it names the ticket granted
        json_data["ticketId"] = int(get_text_element(root, "substances/ticket/ticketName/id"))

    return json_data
