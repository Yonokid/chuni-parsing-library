import xml.etree.ElementTree as ET

from chuni.tables import duelMission
from chuni.utils import get_bool, get_int, get_ref, get_text_element, get_version, safe_find

# 2.20: same MissionSubData as DuelMission plus a playGame block (type 7) and more playMusicResult counters
MISSION_TYPES = {**duelMission.MISSION_TYPES, 7: "playGame"}
_FIELDS = {
    **duelMission._FIELDS,
    "playMusicResult": duelMission._FIELDS["playMusicResult"] + [
        ("maxChain", "maxChain", get_int), ("fullChain", "fullChain", get_bool), ("ajc", "ajc", get_bool),
        ("missNum", "missNum", get_int), ("attackNum", "attackNum", get_int), ("justiceNum", "justiceNum", get_int),
    ],
    "playGame": [
        ("isTicketCredit", "isTicketCredit", get_bool), ("isCharaRankUp", "isCharaRankUp", get_bool),
        ("isPlayerLvUp", "isPlayerLvUp", get_bool), ("isMapStep", "isMapStep", get_bool),
        ("isGamePointGet", "isGamePointGet", get_bool),
    ],
}


def _mission(el: ET.Element) -> dict:
    mission_type = get_int(el, "type")
    kind = MISSION_TYPES[mission_type]
    block = safe_find(el, f"{kind}Data")
    fields = {key: read(block, tag) for key, tag, read in _FIELDS[kind]}
    return {"type": mission_type, "kind": kind, **{k: v for k, v in fields.items() if v}}


def parse_cmissionInfo(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "explainText": get_text_element(root, "explainText"),
        "iconType": get_int(root, "iconType"),
        "unitType": get_int(root, "unitType"),
        "priority": get_int(root, "priority"),
        "conditions": [_mission(m) for m in safe_find(root, "missions/conditions").iter("MissionSubData")],
    }


def parse_cmission(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "netOpen": get_ref(root, "netOpenName"),
        "disableFlag": get_bool(root, "disableFlag"),
        "explainText": get_text_element(root, "explainText"),
        "chara": get_ref(root, "charaImageName"),
        "priority": get_int(root, "priority"),
        "rounds": [{
            "reward": get_ref(r, "rewardName"),
            "targetValue": get_int(r, "targetValue"),
            "isLoop": get_bool(r, "isLoop"),
            "isPickup": get_bool(r, "isPickup"),
        } for r in safe_find(root, "rounds").iter("CMissionDataRoundInfo")],
        "stages": [{
            "stage": get_int(s, "stageValue"),
            "pos": get_int(s, "posValue"),
            "loop": get_int(s, "loopValue"),
            "info": get_ref(s, "cmissionInfoName"),
            "border": get_int(s, "borderValue"),
            "point": get_int(s, "pointValue"),
        } for s in safe_find(root, "stages").iter("CMissionDataStageInfo")],
    }
