import xml.etree.ElementTree as ET

from global_utils import get_text_element
from title import unlock_types


def parse_plate(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "releaseTagName/str").replace('.', '').replace('Ver', ''))
        json_data["name"] = get_text_element(root, "name/str")

        json_data["unlock_category"] = get_text_element(root, "relConds/condition0/Category")
        json_data["unlock_type"] = get_text_element(root, f"relConds/condition0/kind{json_data['unlock_category']}")
        if json_data["unlock_type"] not in unlock_types:
            raise Exception(f"Unknown unlock type: {json_data['unlock_type']}, {json_data['unlock_category']}, {json_data['id']}")

        if json_data["unlock_type"] == "MUSIC" or json_data["unlock_type"] == "TRACK_SKIP":
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/musicId/id"))
        elif json_data["unlock_type"] in ("CHARA_KAKUSEI", "CHARA_KAISU"):
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/charaId/id"))
        elif json_data["unlock_type"] in ("MAP_CHARA_KAKUSEI", "MAP_COMPLETE"):
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/mapId/id"))
        elif json_data["unlock_type"] == "DANNI":
            json_data["reference_id"] = get_text_element(root, "relConds/condition0/gradeId")
        elif json_data["unlock_type"] == "PARTNER":
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/partnerId/id"))
        elif json_data["unlock_type"] == "MUSIC_GENRE_SELECTED":
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/musicGenreId/id"))
        elif json_data["unlock_type"] == "SATELLITE":
            json_data["reference_id"] = get_text_element(root, "relConds/condition0/satelliteId")
        elif json_data["unlock_type"] == "TODOHUKEN_SEIHA":
            json_data["reference_id"] = get_text_element(root, "relConds/condition0/todohukenId")
        json_data["param"] = int(get_text_element(root, "relConds/condition0/param"))

        try:
            json_data["normText"] = get_text_element(root, "normText")
        except Exception:
            json_data["normText"] = ""

    return json_data
