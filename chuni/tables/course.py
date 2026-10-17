import xml.etree.ElementTree as ET

from chuni.utils import (get_bool, get_int, get_ref, get_text_element,
                          safe_find)

# CourseMusicDataInfo.type -> how the song slot is picked
INFO_TYPES = {0: "selectMusic", 1: "selectLevel"}


def _info(el: ET.Element) -> dict:
    info_type = get_int(el, "type")
    data = {"type": info_type, "kind": INFO_TYPES[info_type]}
    if info_type == 0:
        data["music"] = get_ref(el, "selectMusic/musicName")
        data["difficulty"] = get_ref(el, "selectMusic/musicDiff")
    else:
        level = safe_find(el, "selectLevel/fromLevel")
        data["fromLevel"] = {"id": get_int(level, "id"), "name": get_text_element(level, "data")}
    return data

def parse_course(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        root = ET.parse(xml_file).getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["disableFlag"] = get_bool(root, "disableFlag")
        json_data["difficulty"] = {"id": get_int(root, "difficulty/id"), "name": get_text_element(root, "difficulty/data")}
        if root.find("category") is not None:  # dropped in 1.20.00
            json_data["category"] = get_int(root, "category")
        json_data["rule"] = get_ref(root, "rule")  # courseRule/courseRule<name>
        json_data["reward"] = get_ref(root, "reward")
        if root.find("reward2nd") is not None:  # 1.20.00+
            json_data["reward2nd"] = get_ref(root, "reward2nd")
        json_data["priority"] = get_int(root, "priority")
        json_data["infos"] = [_info(i) for i in safe_find(root, "infos").iter("CourseMusicDataInfo")]

    return json_data
