import xml.etree.ElementTree as ET

from global_utils import get_text_element


def parse_chara(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["color"] = get_text_element(root, "color/str")
        json_data["genre"] = get_text_element(root, "genre/str")
        json_data["isCopyright"] = get_text_element(root, "isCopyright").lower() == "true"
        json_data["disable"] = get_text_element(root, "disable").lower() == "true"

        awakening = []
        for awake_elem in root.findall("awakening/CharaAwakeData"):
            awakening.append({
                "index": int(awake_elem.find("index").text),
                "type": awake_elem.find("type").text or "",
                "awakeLevel": int(awake_elem.find("awakeLevel").text),
            })
        json_data["awakening"] = awakening

    return json_data
