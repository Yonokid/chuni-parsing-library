import os
import xml.etree.ElementTree as ET

from chuni.utils import (get_version, get_bool, get_enum_name, get_int, get_ref,
                          get_ref_list, get_text_element, safe_find)


def _ref_names(element: ET.Element, tag: str) -> list:
    return [ref["name"] for ref in get_ref_list(element, f"{tag}/list")]

def _growth(el: ET.Element, tag: str):
    """Int before 2.00; 2.00 (NEW!!) makes it a <SkillGrowthData><value> list per grown level (empty when unused)."""
    node = safe_find(el, tag)
    if len(node) or not (node.text or "").strip():
        return [get_int(item, "value") for item in node.iter("SkillGrowthData")]
    return int(node.text)

def _section(el: ET.Element) -> dict:
    return {
        "rateSetting": get_bool(el, "rateSetting"),
        "startPos": get_int(el, "startPos"),
        "endPos": get_int(el, "endPos"),
    }

def _timing(el: ET.Element) -> dict:
    return {
        "scene": get_int(el, "scene"),
        "useSection": get_bool(el, "useSection"),
        "section": _section(safe_find(el, "section")),
        "missNum": get_int(el, "missNum"),
        **({"jhComboNum": get_int(el, "jhComboNum")} if el.find("jhComboNum") is not None else {}),  # 2.45+
        "comboNum": get_int(el, "comboNum"),
        "chainNum": get_int(el, "chainNum"),
        "chainCut": get_bool(el, "chainCut"),
        "award": get_int(el, "award"),
        "gaugeNum": get_int(el, "gaugeNum"),
        "time": get_int(el, "time"),
        **({"ratio": get_int(el, "ratio")} if el.find("ratio") is not None else {}),
        "judgeAlways": get_bool(el, "judgeAlways"),
        "notesTypes": _ref_names(el, "notesTypes"),
        "notesJudgeResultRange": get_int(el, "notesJudgeResultRange"),
        "notesJudgeResult": get_enum_name(el, "notesJudgeResultID"),
    }

def _precondition(el: ET.Element) -> dict:
    """1.20.00+ gaugeAssist preconditions: A is chara level + ratio, B is an optional extra target."""
    return {tag: int(el.findtext(tag, "0")) if tag != "use" else el.findtext(tag) == "true"
            for tag in ("ratio", "charaLv", "use", "targetType", "targetNum", "expressionType") if el.find(tag) is not None}

def _gauge_assist(el: ET.Element) -> dict:
    return {
        **{k: _precondition(el.find(k)) for k in ("preconditionA", "preconditionB") if el.find(k) is not None},
        "notesGroupJudge": get_bool(el, "notesGroupJudge"),
        "timing": _timing(safe_find(el, "timing")),
        "useNumNoAccess": get_bool(el, "useNumNoAccess"),
        "notesGaugeNoAdd": get_bool(el, "notesGaugeNoAdd"),
        "valueAddGauge": get_int(el, "valueAddGauge"),
        "valueGrowthAddGauge": _growth(el, "valueGrowthAddGauge"),
        "rateAddGauge": get_int(el, "rateAddGauge"),
        "rateGrowthAddGauge": _growth(el, "rateGrowthAddGauge"),
    }

def _gauge_keep(el: ET.Element) -> dict:
    return {"gaugeNum": get_int(el, "gaugeNum"), "section": _section(safe_find(el, "section"))}

def _damage_guard(el: ET.Element) -> dict:
    return {
        "notesTypes": _ref_names(el, "notesTypes"),
        "notesGroupJudge": get_bool(el, "notesGroupJudge"),
        "useNumNoAccess": get_bool(el, "useNumNoAccess"),
        "damageRate": get_int(el, "damageRate"),
        "growthDamageRate": _growth(el, "growthDamageRate"),
        "section": _section(safe_find(el, "section")),
    }

def _death_penalty(el: ET.Element) -> dict:
    return {
        "enableGaugeNum": get_bool(el, "enableGaugeNum"),
        "gaugeNum": get_int(el, "gaugeNum"),
        "notesJudgeResult": get_enum_name(el, "notesJudgeResultID"),
        "countNum": get_int(el, "countNum"),
    }

SUBSTANCES = {
    0: ("gaugeAssist", _gauge_assist),
    1: ("gaugeKeep", _gauge_keep),
    2: ("damageGuard", _damage_guard),
    3: ("deathPenalty", _death_penalty),
    4: ("changeJudgeIni", lambda el: {"iniFile": get_ref(el, "iniFileName")}),
    5: ("changeJudgeResult", lambda el: {"notesJudgeResult": get_enum_name(el, "notesJudgeResultID")}),
    6: ("changeSpeed", lambda el: {"playOptionSpeed": get_enum_name(el, "playOptionSpeedID")}),
    7: ("changeImg", lambda el: {"imgType": get_int(el, "imgType")}),
}

def parse_substance(sub: ET.Element) -> dict:
    substance_type = get_int(sub, "type")
    tag, parse = SUBSTANCES[substance_type]
    el = safe_find(sub, tag)
    return {"type": substance_type, "kind": tag, "skillIconType": get_int(el, "skillIconType"), **parse(el)}

def parse_skill(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["category"] = int(get_text_element(root, "category/id" if root.find("category/id") is not None else "category"))
        json_data["rareType"] = int(root.findtext("rareType", "0"))  # 2.00: skills are seeds, no rarity/price/force level
        json_data["counterType"] = int(get_text_element(root, "counterType"))
        json_data["maxLv"] = int(get_text_element(root, "maxLv"))
        json_data["forceLv"] = int(root.findtext("forceLv", "0"))
        json_data["useLimit"] = get_text_element(root, "useLimit") == "true"
        json_data["useNum"] = int(get_text_element(root, "useNum"))
        json_data["growthUseNum"] = _growth(root, "growthUseNum")
        json_data["price"] = int(root.findtext("price", "0"))
        json_data["defaultHave"] = get_bool(root, "defaultHave")
        json_data["chgInvalidColor"] = root.findtext("chgInvalidColor", "false") == "true"
        json_data["priority"] = get_int(root, "priority")

        if root.find("seedName") is not None:  # 2.00+: the seed item that levels the skill
            json_data["seedName"] = get_text_element(root, "seedName")
            json_data["growthExLv"] = _growth(root, "growthExLv")
        if root.find("releaseTagName") is not None:
            json_data["releaseTagName"] = get_text_element(root, "releaseTagName/str")
        json_data["targetCharas"] = get_ref_list(root, "targetCharaNames/list") if root.find("targetCharaNames") is not None else []
        json_data["substances"] = [
            parse_substance(sub) for sub in safe_find(root, "substances").iter("SkillSubstanceData")
        ]

        info_path = get_text_element(root, "infoTxtFile/path")
        explain_text = []
        if info_path:
            full_info_path = os.path.join(os.path.dirname(file), info_path)
            if os.path.exists(full_info_path):
                with open(full_info_path, "r", encoding="utf-8") as info_file:
                    explain_text = [
                        line.strip()
                        for line in info_file.readlines()
                        if line.strip()
                    ]
        json_data["explainText"] = explain_text

    return json_data
