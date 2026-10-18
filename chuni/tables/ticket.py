import xml.etree.ElementTree as ET

from chuni.utils import get_text_element, get_version


def parse_ticket(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["type"] = int(get_text_element(root, "type"))
        json_data["stockMaxNum"] = int(get_text_element(root, "stockMaxNum"))
        json_data["explainText"] = root.findtext("explainText", "")
        # PLUS+ nests the values in one <substances> child per ticket type, ordered by type
        substances = root.find("substances")
        if substances is not None:
            kinds = [c for c in substances if c.tag not in ("resourceVersion", "type")]
            src = kinds[int(get_text_element(substances, "type"))]
        else:
            src = root
        for key in ("valueDay", "valueDayRaw", "valueUse", "valueUseRaw", "valueBoost", "valueBoostRaw",
                    "valuePlusRaw", "valueMultiple", "valueMultipleRaw", "addRankLimit"):
            json_data[key] = int(src.findtext(key, "0"))
        json_data["priority"] = int(get_text_element(root, "priority"))

    return json_data
