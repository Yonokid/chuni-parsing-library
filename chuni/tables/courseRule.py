import xml.etree.ElementTree as ET

from chuni.utils import get_int, get_text_element, line_break


def parse_courseRule(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": int(get_text_element(root, "resourceVersion/str")),
        "name": get_text_element(root, "name/str"),
        "explain": line_break(root.findtext("explain")),
        "life": get_int(root, "life"),
        "recoveryLife": int(root.findtext("recovery_life", "0")),  # absent in 1.15.00
        "clearLife": get_int(root, "clear_life"),
        "damageMiss": get_int(root, "damage_miss"),
        "damageAttack": get_int(root, "damage_attack"),
        "damageJustice": get_int(root, "damage_justice"),
        "damageJusticeCritical": get_int(root, "damage_justice_c"),
    }
