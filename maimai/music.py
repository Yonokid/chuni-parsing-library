import xml.etree.ElementTree as ET

from global_utils import get_text_element


DIFFICULTY_INDEX = ["Basic", "Advanced", "Expert", "Master", "Re:Master", "Utage"]


def parse_music(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["sortName"] = get_text_element(root, "sortName")
        json_data["artist"] = get_text_element(root, "artistName/str")
        json_data["bpm"] = int(get_text_element(root, "bpm"))
        json_data["version"] = int(get_text_element(root, "version"))
        json_data["addVersion"] = get_text_element(root, "AddVersion/str")
        json_data["genre"] = get_text_element(root, "genreName/str")
        json_data["disable"] = get_text_element(root, "disable").lower() == "true"

        notes_data = []
        for i, notes_elem in enumerate(root.findall("notesData/Notes")):
            level = int(notes_elem.find("level").text)
            level_decimal = int(notes_elem.find("levelDecimal").text)
            is_enable = notes_elem.find("isEnable").text.lower() == "true"
            notes_type = int(notes_elem.find("notesType").text)
            designer = notes_elem.find("notesDesigner/str").text or ""
            file_path = notes_elem.find("file/path").text or ""

            notes_data.append({
                "difficulty": DIFFICULTY_INDEX[i] if i < len(DIFFICULTY_INDEX) else str(i),
                "level": level,
                "levelDecimal": level_decimal,
                "notesDesigner": designer,
                "notesType": notes_type,
                "isEnable": is_enable,
                "file": file_path,
            })

        json_data["notes"] = notes_data

    return json_data
