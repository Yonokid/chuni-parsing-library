import json
import os
import xml.etree.ElementTree as ET

from chuni.utils import (get_version, get_bool, get_int, get_ref, get_text_element,
                          line_break, safe_find)

# CourseMusicDataInfo.type -> how the song slot is picked
INFO_TYPES = {0: "selectMusic", 1: "selectLevel", 2: "selectMusicList"}  # 2: 1.45


def _info(el: ET.Element) -> dict:
    info_type = get_int(el, "type")
    data = {"type": info_type, "kind": INFO_TYPES[info_type]}
    if info_type == 0:
        data["music"] = get_ref(el, "selectMusic/musicName")
        data["difficulty"] = get_ref(el, "selectMusic/musicDiff")
    elif info_type == 2:
        lst = safe_find(el, "selectMusicList")
        data["musicList"] = [
            {"music": get_ref(m, "courseMusicData/name"), "difficulty": get_ref(m, "courseMusicData/diff")}
            for m in lst.iter("CourseMusicListSubData")
        ]
        data["isRecordShown"] = get_bool(lst, "isRecordShown")
    else:
        level = safe_find(el, "selectLevel/fromLevel")
        data["fromLevel"] = {"id": get_int(level, "id"), "name": get_text_element(level, "data")}
    return data

def parse_course(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        root = ET.parse(xml_file).getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
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
        if root.find("conditionsCourse") is not None:  # 2.05: unlocked by clearing another course
            json_data["conditionsCourse"] = get_ref(root, "conditionsCourse")
            json_data["conditionsText"] = line_break(root.findtext("conditionsText"))
        json_data["infos"] = [_info(i) for i in safe_find(root, "infos").iter("CourseMusicDataInfo")]

    return json_data

def embed_course_rules(output_dir: str) -> None:
    """Inlines each course's rule (courseRule.json: life, damage, explanation) into course.json: it only makes sense as part of a course."""
    course_path, rule_path = (os.path.join(output_dir, n, f"{n}.json") for n in ("course", "courseRule"))
    if not (os.path.exists(course_path) and os.path.exists(rule_path)):
        return
    with open(rule_path, "r", encoding="utf-8") as f:
        rules = {r["id"]: r for r in json.load(f)}
    with open(course_path, "r", encoding="utf-8") as f:
        courses = json.load(f)
    for course in courses:
        rule = rules.get((course["rule"] or {}).get("id"))
        if rule:
            course["rule"] = rule
    with open(course_path, "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=4, ensure_ascii=False)
