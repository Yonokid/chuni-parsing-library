import xml.etree.ElementTree as ET

from chuni.utils import get_int, get_ref, get_text_element, safe_find


def parse_reward(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        # every reward holds exactly one substance; type picks which field is set
        sub = safe_find(root, "substances/list/RewardSubstanceData")
        json_data["type"] = get_int(sub, "type")
        json_data["gamePoint"] = get_int(sub, "gamePoint/gamePoint")
        for key in ("ticket", "trophy", "chara", "skill", "namePlate", "music", "mapIcon", "systemVoice"):
            json_data[key] = get_ref(sub, f"{key}/{key}Name")

    return json_data
