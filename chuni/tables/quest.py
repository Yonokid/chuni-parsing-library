import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_ref, get_ref_list, get_text_element, safe_find


def parse_quest(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        root = ET.parse(xml_file).getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["disableFlag"] = get_bool(root, "disableFlag")
        json_data["charaWorks"] = get_ref_list(root, "charaWorks/list")
        json_data["charas"] = get_ref_list(root, "charas/list")
        json_data["priority"] = get_int(root, "priority")
        json_data["rewards"] = [{
            "sumRank": get_int(i, "sumRank"),
            "trophy": get_ref(i, "keyTrophyName"),
            "namePlate": get_ref(i, "keyNamePlateName"),
            "rewards": get_ref_list(i, "rewardName/list"),
        } for i in safe_find(root, "info").iter("QuestRewardDataInfo")]

    return json_data
