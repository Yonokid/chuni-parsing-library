import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_ref, get_text_element, get_version, safe_find


def parse_duel(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "explainText": get_text_element(root, "explainText"),
        "priority": get_int(root, "priority"),
        "rounds": [{
            "chara": get_ref(r, "charaName"),
            "charaImage": get_text_element(r, "charaImageName/str"),
            "charaVoice": get_ref(r, "charaVoiceName"),
            "background": get_ref(r, "backgroundName"),
            "reward": get_ref(r, "rewardName"),
            "targetValue": get_int(r, "targetValue"),
            "progressType": get_int(r, "pogressType"),  # sic: game's own spelling
            "resolution": get_int(r, "resolution"),
        } for r in safe_find(root, "rounds").iter("DuelDataRoundInfo")],
    }
