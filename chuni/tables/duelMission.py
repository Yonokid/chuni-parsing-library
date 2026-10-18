import xml.etree.ElementTree as ET

from chuni.utils import (get_version, get_bool, get_int, get_ref, get_ref_list,
                          get_text_element, safe_find)

# MissionSubData.type -> active sub-struct (deserializer field order; 0/2/3 confirmed by the shipped data).
MISSION_TYPES = {0: "playMusic", 1: "playSetting", 2: "playMusicResult", 3: "playCourse", 4: "chara", 5: "skill", 6: "playNetBattle"}

# per sub-struct: (output key, tag, reader); only populated fields are kept
_FIELDS = {
    "playMusic": [
        ("level", "level", get_int), ("levelPlus", "levelPlus", get_bool),
        ("genres", "genreNames/list", get_ref_list), ("musics", "musicNames/list", get_ref_list),
        ("difficulty", "musicDif", get_ref), ("sortGenre", "optionSortMusicGenre", get_ref),
        ("filterGenre", "filterGenreName", get_ref), ("filterVersion", "filterVerName", get_ref),
        ("filterWordCategory", "filterWordCategory", get_int),
        ("newMusic", "newMusic", get_bool), ("randomSelect", "randomSelect", get_bool),
    ],
    "playSetting": [
        ("tapSe", "playOptionTapSe", get_ref), ("mirror", "playOptionMirror", get_bool),
        ("fieldColor", "playOptionFieldColor", get_ref),
    ],
    "playMusicResult": [
        ("scoreRank", "scoreRank", get_ref), ("gameOver", "gameOver", get_bool),
        ("gameClear", "gameClear", get_bool), ("newRecord", "newRecord", get_bool),
        ("maxCombo", "maxCombo", get_int), ("fullCombo", "fullCombo", get_bool),
        ("allJustice", "allJustice", get_bool),
    ],
    "playCourse": [
        ("courseDifficulty", "courseDif", get_ref), ("courseClear", "courseClear", get_bool),
        ("scoreRank", "scoreRank", get_ref),
    ],
    "chara": [("chara", "chara", get_ref), ("charaWorks", "charaWorks", get_ref)],
    "skill": [("category", "category", get_ref)],
    "playNetBattle": [("isNetBattlePlay", "isNetBattlePlay", get_bool)],
}


def _mission(el: ET.Element) -> dict:
    mission_type = get_int(el, "type")
    kind = MISSION_TYPES[mission_type]
    block = safe_find(el, f"{kind}Data")
    fields = {key: read(block, tag) for key, tag, read in _FIELDS[kind]}
    return {"type": mission_type, "kind": kind, **{k: v for k, v in fields.items() if v}}


def parse_duelMission(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "explainText": get_text_element(root, "explainText"),
        "categoryType": get_int(root, "categoryType"),
        "weight": get_int(root, "weight"),
        "priority": get_int(root, "priority"),
        "conditions": [_mission(m) for m in safe_find(root, "missions/conditions").iter("MissionSubData")],
    }
