import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import (get_version, get_bool, get_int, get_ref, get_ref_list,
                          get_text_element, line_break, safe_find)

# EventData.substances.type -> active sub-struct (deserializer field order; matches shipped data).
SUBSTANCES = {
    0: ("flag", lambda el: {"value": get_int(el, "value")}),
    1: ("information", lambda el: {
        "informationType": get_int(el, "informationType"),
        "text": line_break(el.findtext("text")),
        "image": get_text_element(el, "image/path"),
        "movie": get_ref(el, "movieName"),
        # PLUS+ only
        **({"courses": get_ref_list(el, "courseNames/list"),
            "presents": get_ref_list(el, "presentNames/list")} if el.find("courseNames") is not None else {}),
        # mapType: PLUS+ only; mapFilterID replaces it from 1.20.00
        **({"mapType": get_int(el, "mapType")} if el.find("mapType") is not None else {}),
        **({"mapFilter": get_ref(el, "mapFilterID")} if el.find("mapFilterID") is not None else {}),
    }),
    2: ("map", lambda el: {
        "tagText": get_text_element(el, "tagText"),
        "map": get_ref(el, "mapName"),
        "musics": get_ref_list(el, "musicNames/list"),
    }),
    3: ("music", lambda el: {"musics": get_ref_list(el, "musicNames/list")}),
    4: ("advertiseMovie", lambda el: {
        "firstMovie": get_ref(el, "firstMovieName"),
        "secondMovie": get_ref(el, "secondMovieName"),
    }),
    5: ("recommendMusic", lambda el: {"musics": get_ref_list(el, "musicNames/list")}),
    6: ("release", lambda el: {"value": get_int(el, "value")}),
    7: ("course", lambda el: {"courses": get_ref_list(el, "courseNames/list")}),
    8: ("quest", lambda el: {"quests": get_ref_list(el, "questNames/list")}),
    9: ("duel", lambda el: {"duel": get_ref(el, "duelName")}),
    10: ("changeSurfBoardUI", lambda el: {"value": get_int(el, "value")}),
    11: ("rightsInfo", lambda el: {"rights": get_ref_list(el, "rightsNames/list")}),
    12: ("battleReward", lambda el: {"battleReward": get_ref(el, "battleRewardName")}),
    13: ("dailyBonusPreset", lambda el: {"dailyBonusPreset": get_ref(el, "dailyBonusPresetName")}),  # 2.05
}
# 2.10: type 12 holds a playRewardSet instead of a battleReward
PLAY_REWARD_SET = ("playRewardSet", lambda el: {"playRewardSet": get_ref(el, "playRewardSetName")})
# 2.05: type 10 holds a gacha id in avatarAccessoryGacha (changeSurfBoardUI is 0 there)
GACHA = ("avatarAccessoryGacha", lambda el: {"gacha": get_ref(el, "avatarAccessoryGachaName")})


def parse_event(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["ddsBannerId"] = get_text_element(root, "ddsBannerName/id")
        json_data["eventBannerName"] = get_text_element(root, "substances/information/image/path")
        json_data["text"] = line_break(root.findtext("text"))  # optional: game keeps default when absent
        json_data["periodDispType"] = get_int(root, "periodDispType")
        json_data["alwaysOpen"] = get_bool(root, "alwaysOpen")
        json_data["priority"] = get_int(root, "priority")
        for flag in ("teamOnly", "isKop"):  # 2.00+
            if root.find(flag) is not None:
                json_data[flag] = get_bool(root, flag)
        if root.find("isAou") is not None:
            json_data["isAou"] = get_bool(root, "isAou")

        substances = safe_find(root, "substances")
        substance_type = get_int(substances, "type")
        tag, parse = SUBSTANCES[substance_type]
        gacha = substances.find("avatarAccessoryGacha")
        if substance_type == 10 and gacha is not None and get_ref(gacha, "avatarAccessoryGachaName"):
            tag, parse = GACHA
        if substance_type == 12 and substances.find("playRewardSet") is not None:
            tag, parse = PLAY_REWARD_SET
        json_data["substance"] = {"type": substance_type, "kind": tag, **parse(safe_find(substances, tag))}

    return json_data

def copy_eventBanner(input: str, event: dict, output: str):
    img = Image.open(os.path.join(input, event["eventBannerName"]))
    img.save(os.path.join(output, f"{event["eventBannerName"]}.webp"))

def copy_ddsBanner(input: str, event: dict, output: str) -> None:
    files = os.listdir(input)
    dds_files = [f for f in files if f.endswith('.dds')]
    filename = os.path.splitext(dds_files[0])[0]
    img = Image.open(os.path.join(input, dds_files[0]))
    event["ddsBannerName"] = f"{filename}.webp"
    img.save(os.path.join(output, f"{filename}.webp"))
