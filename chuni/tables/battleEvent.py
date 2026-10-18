import xml.etree.ElementTree as ET

from chuni.utils import get_int, get_text_element, get_version


def parse_battleEvent(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "type": get_int(root, "type"),
        "scoreDivVal": get_int(root, "scoreDivVal"),
        "fumenLevelDivVal": get_int(root, "fumenLevelDivVal"),
        **({"netBattleModeRateVal": get_int(root, "netBattleModeRateVal")} if root.find("netBattleModeRateVal") is not None else {}),  # 2.30+
        # points awarded per placement, 1st to last
        "rankPoints": [get_int(d, "val") for d in root.iterfind("rankPointDataList/RankPointData")],
    }
