"""Parsers for the small reference/table XML types (iniFile, rightsInfo, gauge, gameTable, ranking)."""
import configparser
import os
import xml.etree.ElementTree as ET

from chuni.utils import get_int, get_ref, get_text_element, safe_find


def _header(file: str) -> tuple[ET.Element, dict]:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()
    return root, {
        "id": int(get_text_element(root, "name/id")),
        "version": int(get_text_element(root, "resourceVersion/str")),
        "name": get_text_element(root, "name/str"),
    }

def parse_iniFile(file: str) -> dict:
    root, data = _header(file)
    data["iniFile"] = get_text_element(root, "iniFile/path")
    ini_path = os.path.join(os.path.dirname(file), data["iniFile"])
    if os.path.exists(ini_path):
        ini = configparser.ConfigParser()
        ini.optionxform = str
        ini.read(ini_path, encoding="utf-8-sig")
        data["values"] = {
            section: {key: int(value) if value.lstrip("-").isdigit() else value for key, value in ini[section].items()}
            for section in ini.sections()
        }
    return data

def parse_rightsInfo(file: str) -> dict:
    root, data = _header(file)
    data["type"] = get_int(root, "type")
    data["image"] = get_text_element(root, "image/path")
    return data

def parse_gauge(file: str) -> dict:
    root, data = _header(file)
    data["fumens"] = [
        {
            "difficulty": int(get_text_element(fumen, "type/id")),
            "difficultyName": get_text_element(fumen, "type/data"),
            "normGauge": get_int(fumen, "normGauge"),
            "maxGauge": get_int(fumen, "maxGauge"),
            "recoveryGauge": get_int(fumen, "recoveryGauge"),
        }
        for fumen in safe_find(root, "fumens").iter("GaugeFumenData")
    ]
    return data

def parse_gameTable(file: str) -> dict:
    root, data = _header(file)
    data["tableType"] = get_int(root, "tableType")
    data["records"] = [
        {
            "type": get_int(record, "type"),
            "str0": get_text_element(record, "valueSet/str0"),
            "value0": get_int(record, "valueSet/value0"),
            "value1": get_int(record, "valueSet/value1"),
        }
        for record in safe_find(root, "records").iter("GameTableRecordData")
    ]
    return data

def parse_ranking(file: str) -> dict:
    root, data = _header(file)
    data["type"] = get_int(root, "type")
    data["ranking"] = [
        {"point": get_int(element, "point"), "ranker": get_ref(element, "rankerName")}
        for element in safe_find(root, "ranking").iter("RankingElement")
    ]
    return data
