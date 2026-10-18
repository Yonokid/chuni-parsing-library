import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_text_element, get_version


def parse_symbolChat(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "sortName": get_text_element(root, "sortName"),
        "text": get_text_element(root, "text"),
        "balloonId": get_int(root, "balloonID"),
        "scenes": [get_int(scene, "sceneID") for scene in root.iter("SymbolChatSceneData")],
        "defaultHave": get_bool(root, "defaultHave"),
        "explainText": get_text_element(root, "explainText"),
        "priority": get_int(root, "priority"),
    }
