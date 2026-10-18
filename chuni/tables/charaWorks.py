import xml.etree.ElementTree as ET

from chuni.utils import get_int, get_text_element, get_version


def parse_charaWorks(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "sortName": root.findtext("sortName"),
        "priority": get_int(root, "priority"),
    }
