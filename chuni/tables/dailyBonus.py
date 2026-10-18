import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_ref_list, get_text_element, get_version, line_break

# effect block -> value tags read when <isEnabled> is true
EFFECTS = {
    "mapGridData": ["addValue"],
    "charaExpData": ["addValue"],
    "avatarPointData": ["multiplyValue"],
    "avatarChanceData": [],
    "duelCriticalData": ["criticalRateOnNormal", "criticalRateOnTodome"],
    "gamePointData": ["count"],
}


def parse_dailyBonus(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "text": line_break(root.findtext("text")),
        "effects": {
            tag: {k: get_int(root, f"{tag}/{k}") for k in keys}
            for tag, keys in EFFECTS.items() if get_bool(root, f"{tag}/isEnabled")
        },
    }


def parse_dailyBonusPreset(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "dailyBonuses": get_ref_list(root, "dailyBonusNames/list"),
    }
