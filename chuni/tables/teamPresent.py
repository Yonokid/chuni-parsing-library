import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_ref, get_text_element, get_version


def parse_teamPresent(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "present": get_ref(root, "present"),
        "itemNum": get_int(root, "itemNum"),
        "needTeamPoint": get_int(root, "needTeamPoint"),
        "category": get_int(root, "teamPresentCategoryType"),
    }
