import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_ref, get_text_element, get_version


def parse_playReward(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "type": get_int(root, "type"),
        "reward": get_ref(root, "rewardName"),
        "point": get_int(root, "point"),
        "isPickUpReward": get_bool(root, "isPickUpReward"),
    }


def parse_playRewardSet(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "playRewards": [get_ref(i, "playRewardName") for i in root.iterfind("infoList/PlayRewardDataInfo")],
    }
