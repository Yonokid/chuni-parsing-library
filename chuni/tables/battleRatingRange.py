import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_text_element, get_version


def parse_battleRatingRange(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "minBattleRating": get_int(root, "minBattleRating"),
        "minMusicLevel": get_int(root, "minMusicLevel"),
        "maxMusicLevel": get_int(root, "maxMusicLevel"),
        # one flag per difficulty slot, in game order
        "selectableByCPU": [get_bool(d, "isSelectableByCPU") for d in root.iterfind("musicDifDataList/MusicDifData")],
    }
