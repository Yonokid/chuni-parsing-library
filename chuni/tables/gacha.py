import os
import shutil
import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_text_element, get_version

RARITIES = ("N", "R", "SR", "SSR")


def parse_gacha(file: str) -> dict:
    """Card gacha (the card ids are not otherwise present in the data)."""
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "gachaName"),
        "disableFlag": get_bool(root, "disableFlag"),
        "ceilingNum": get_int(root, "ceilingNum"),
        "ceilingType": get_int(root, "ceilingType"),
        "gachaType": get_int(root, "gachaType"),
        "gachaPickup": get_int(root, "gachaPickup"),
        "rarity": {
            r: {key: get_int(root, f"rare{key}{r}") for key in ("Ratio", "Change", "Pickup")} for r in RARITIES
        },
        "cards": [
            {"id": get_int(info, "cardName/id"), "weight": get_int(info, "weight"), "pickup": get_int(info, "pickup")}
            for info in root.iter("GachaCardDataInfo")
        ],
        "priority": get_int(root, "priority"),
        "imageFile": get_text_element(root, "image/path"),
        "imageSmallFile": get_text_element(root, "imageSmall/path"),
    }

def copy_gacha_image(input: str, gacha: dict, output: str) -> None:
    for key in ("imageFile", "imageSmallFile"):
        if gacha[key]:
            shutil.copyfile(os.path.join(input, gacha[key]), os.path.join(output, gacha[key]))
