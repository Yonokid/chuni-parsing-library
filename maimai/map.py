import xml.etree.ElementTree as ET

from global_utils import get_text_element


def parse_map(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["isCollabo"] = get_text_element(root, "IsCollabo").lower() == "true"
        json_data["isInfinity"] = get_text_element(root, "IsInfinity").lower() == "true"
        json_data["island"] = get_text_element(root, "IslandId/str")
        json_data["color"] = get_text_element(root, "ColorId/str")
        json_data["bonusMusicId"] = int(get_text_element(root, "BonusMusicId/id"))
        json_data["bonusMusicMagnification"] = int(get_text_element(root, "BonusMusicMagnification"))
        json_data["openEventId"] = int(get_text_element(root, "OpenEventId/id"))
        json_data["findText"] = get_text_element(root, "FindText")
        json_data["selectText"] = get_text_element(root, "SelectText")

        treasures = []
        for t in root.findall("TreasureExDatas/MapTreasureExData"):
            treasures.append({
                "distance": int(t.find("Distance").text),
                "flag": t.find("Flag").text or "",
                "treasureId": int(t.find("TreasureId/id").text),
                "treasure": t.find("TreasureId/str").text or "",
            })
        json_data["treasures"] = treasures

    return json_data
