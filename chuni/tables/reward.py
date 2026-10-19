import xml.etree.ElementTree as ET

from chuni.utils import get_int, get_ref, get_text_element, get_version, safe_find


def parse_reward(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        # every reward holds exactly one substance; type picks which field is set
        sub = root.find("substances/list/RewardSubstanceData")
        if sub is None:  # 2.00 reward 0 ("none") has no substance
            sub = ET.Element("RewardSubstanceData", {})
            ET.SubElement(sub, "type").text = "-1"
            ET.SubElement(ET.SubElement(sub, "gamePoint"), "gamePoint").text = "0"
        json_data["type"] = get_int(sub, "type")
        json_data["gamePoint"] = get_int(sub, "gamePoint/gamePoint")
        if sub.find("skillSeed") is not None:  # 2.00+: skills are granted as seeds (with a count)
            json_data["skillSeedCount"] = get_int(sub, "skillSeed/skillSeedCount")
        for key in ("skillSeed", "avatarAccessory", "frame", "stage"):  # stage: 2.40
            if sub.find(key) is not None:
                json_data[key] = get_ref(sub, f"{key}/{key}Name")
        if sub.find("symbolChat") is not None:  # 2.20+ (never set in shipped data)
            json_data["symbolChat"] = get_ref(sub, "symbolChat/symbolChatName")
        if sub.find("ultimaScore") is not None:
            json_data["ultimaScore"] = get_ref(sub, "ultimaScore/musicName")
        for key in ("ticket", "trophy", "chara", "skill", "namePlate", "music", "mapIcon", "systemVoice"):
            json_data[key] = get_ref(sub, f"{key}/{key}Name")

    return json_data
