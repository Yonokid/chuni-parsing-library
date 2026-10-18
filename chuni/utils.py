import xml.etree.ElementTree as ET


def safe_find(path: ET.Element, element: str, message: str="Element not found") -> ET.Element:
    found_element = path.find(element)
    if found_element is None:
        raise ValueError(message)
    return found_element

def line_break(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace(r"\n", "\n")

def get_text_element(element: ET.Element, tag: str):
    text_element = safe_find(element, tag).text
    return line_break(text_element)

def get_version(root: ET.Element) -> int:
    """<resourceVersion><str>, always 10000 where present; dropped in 2.00 (NEW!!)."""
    return int(root.findtext("resourceVersion/str", "10000"))

def get_ref(element: ET.Element, tag: str):
    """Resolves a <tag><id>/<str> cross-reference to another asset. None if unset (id -1) or absent."""
    if element.find(tag) is None:  # e.g. mapIcon/systemVoice `works` dropped in 1.40
        return None
    id_value = int(get_text_element(element, f"{tag}/id"))
    if id_value < 0:
        return None
    return {"id": id_value, "name": get_text_element(element, f"{tag}/str")}

def get_ref_list(element: ET.Element, tag: str):
    """Resolves a <tag><list><StringID>.../StringID></list></tag> list of cross-references."""
    refs = []
    for item in safe_find(element, tag).iter("StringID"):
        id_value = int(get_text_element(item, "id"))
        if id_value < 0:
            continue
        refs.append({"id": id_value, "name": get_text_element(item, "str")})
    return refs

def get_int(element: ET.Element, tag: str) -> int:
    return int(get_text_element(element, tag))

def get_bool(element: ET.Element, tag: str) -> bool:
    return get_text_element(element, tag) == "true"

def text_or_none(element: ET.Element, tag: str):
    text = get_text_element(element, tag)
    return None if text == "Invalid" else text

def get_enum_name(element: ET.Element, tag: str):
    """Table-backed enum (<tag><id/><str/>): the game resolves it by <str>, ignoring <id>. None if unset."""
    text = text_or_none(element, f"{tag}/str")
    return None if text in ("", "None") else text

def parse_open_condition(element: ET.Element) -> dict:
    """<openCondition> shared by trophy/shop: gate on owning one of eventNames when useCondition is set."""
    data = {"useCondition": get_bool(element, "useCondition")}
    if element.find("forceHide") is not None:
        data["forceHide"] = get_bool(element, "forceHide")
    data["events"] = get_ref_list(element, "eventNames/list")
    return data

def int_or_none(element: ET.Element, tag: str):
    value = int(get_text_element(element, tag))
    return value if value > 0 else None

def parse_condition(cond: ET.Element) -> dict:
    """Compacts a ConditionSubData block (shared by trophy/chara unlock conditions) down to only its populated fields."""
    data = dict()
    data["type"] = int(get_text_element(cond, "type"))

    event_names = get_ref_list(cond, "eventData/eventNames/list")
    if event_names:
        data["events"] = event_names

    genre_names = [
        get_text_element(item, "str")
        for item in safe_find(cond, "playMusicData/genreNames/list").iter("StringID")
    ]
    if genre_names:
        data["genres"] = genre_names

    music_names = get_ref_list(cond, "playMusicData/musicNames/list")
    if music_names:
        data["musics"] = music_names

    music = get_ref(cond, "musicData/musicName")
    if music:
        data["music"] = music
    music_diff = text_or_none(cond, "musicData/musicDif/str")
    if music_diff:
        data["musicDifficulty"] = music_diff

    score_rank = text_or_none(
        cond, "musicData/scoreRank/str"
    ) or text_or_none(cond, "playMusicResultData/scoreRank/str")
    if score_rank:
        data["scoreRank"] = score_rank

    for flag in ("fullCombo", "fullChain", "allJustice"):
        if get_text_element(cond, f"playMusicResultData/{flag}") == "true":
            data[flag] = True
    if get_text_element(cond, "musicData/masterUnderAll") == "true":
        data["masterUnderAll"] = True
    if get_text_element(cond, "playMusicResultData/gameOver") == "true":
        data["gameOver"] = True

    member_num = int_or_none(cond, "playMusicResultData/memberNum")
    if member_num:
        data["memberNum"] = member_num
    miss_num = int_or_none(cond, "playMusicResultData/missNum")
    if miss_num:
        data["missNum"] = miss_num
    play_num = int_or_none(cond, "musicData/playNum")
    if play_num:
        data["playNum"] = play_num

    other_trophy = get_ref(cond, "playMusicResultData/memberOtherTrophyName")
    if other_trophy:
        data["memberOtherTrophy"] = other_trophy

    for field, tag in (
        ("playerRebirthCount", "personData/playerRebirthCount"),
        ("playerLv", "personData/playerLv"),
        ("playerRating", "personData/playerRating"),
        ("totalGamePoint", "personData/totalGamePoint"),
    ):
        value = int_or_none(cond, tag)
        if value:
            data[field] = value

    if cond.find("charaData/rankMax") is not None:  # replaced by targetRank in 1.45
        if get_text_element(cond, "charaData/rankMax") == "true":
            data["anyCharaRankMax"] = True
    target_rank = int_or_none(cond, "charaData/targetRank")
    if target_rank:
        data["charaTargetRank"] = target_rank
    if get_text_element(cond, "skillData/lvMax") == "true":
        data["anySkillLvMax"] = True

    if cond.find("personData/battleRank") is not None:  # 2.00+ net battle
        battle_rank = get_enum_name(cond, "personData/battleRank")
        if battle_rank:
            data["battleRank"] = battle_rank
        for field, tag in (("totalNetBattle", "personData/totalNetBattle"), ("lapNum", "travelData/lapNum")):
            value = int_or_none(cond, tag)
            if value:
                data[field] = value

    have_trophies = get_ref_list(cond, "trophyData/haveTrophyNames/list")
    if have_trophies:
        data["haveTrophies"] = have_trophies

    if cond.find("completeData") is not None:  # 2.30+: clear every song of a release tag at this rank / all-justice
        complete = {}
        tag = get_ref(cond, "completeData/releaseTagName")
        if tag:
            complete["releaseTag"] = tag
        rank = text_or_none(cond, "completeData/scoreRank/str")
        if rank:
            complete["scoreRank"] = rank
        if get_text_element(cond, "completeData/allJustice") == "true":
            complete["allJustice"] = True
        if complete:
            data["complete"] = complete

    region = text_or_none(cond, "travelData/japanRegionID/data")
    if region:
        data["japanRegion"] = region
    region_play_num = int_or_none(cond, "travelData/japanRegionPlayNum")
    if region_play_num:
        data["japanRegionPlayNum"] = region_play_num

    return data

def parse_conditions(root: ET.Element) -> list:
    """Parses a <normCondition><conditions>...</conditions></normCondition> block."""
    return [
        parse_condition(cond)
        for cond in safe_find(root, "normCondition/conditions").iter("ConditionSubData")
    ]


def xml_name(data_type: str) -> str:
    """File name of a data type's per-item XML: Music.xml for music, but CMission.xml for cmission."""
    return {"cmission": "CMission", "cmissionInfo": "CMissionInfo"}.get(data_type, f"{data_type[0].upper()}{data_type[1:]}") + ".xml"
