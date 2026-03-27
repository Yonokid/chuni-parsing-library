import xml.etree.ElementTree as ET

from global_utils import get_text_element

rare_type_map = {
    "Normal": 0,
    "Bronze": 1,
    "Silver": 2,
    "Gold": 3,
    "Rainbow": 4
}
unlock_types = {
    "CHARA_KAKUSEI",
    "MUSIC",
    "MAP_KYORI",
    "None",
    "DANNI",
    "MAP_CHARA_KAKUSEI",
    "TODOHUKEN",
    "RATING",
    "LOGIN_RUIKEI",
    "LOGIN_RENZOKU",
    "MUSIC_GROUP",
    "CHARA_KAISU",
    "NPC_OTOMODACHI_N_REN_WIN",
    "MAI2DX_N_PLAY",
    "ZENKOKU_OTOMODACHI_N_WIN",
    "OTOMODACHI_WIN",
    "NPC_OTOMODACHI_N_WIN",
    "ZENKOKU_OTOMODACHI_N_REN_WIN",
    "MAP_COMPLETE",
    "TRACK_SKIP",
    "PARTNER",
    "TOTAL_CHARA_KAKUSEI",
    "MUSIC_GENRE_SELECTED",
    "TITLESET_DP",
    "MATCHING_FOR_TITLESETPLAYER",
    "FULLCOMBO_COUNT"
}
def parse_title(file: str) -> dict:
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
            raise Exception(f"Unknown unlock type: {json_data['unlock_type']}, {json_data['unlock_category']}, {json_data["id"]}")

        if json_data["unlock_type"] == "MUSIC" or json_data["unlock_type"] == "TRACK_SKIP":
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/musicId/id"))
        elif json_data["unlock_type"] == "CHARA_KAKUSEI" or json_data["unlock_type"] == "CHARA_KAISU":
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/charaId/id"))
        elif json_data["unlock_type"] == "MAP_CHARA_KAKUSEI" or json_data["unlock_type"] == "MAP_COMPLETE":
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/mapId/id"))
        elif json_data["unlock_type"] == "DANNI":
            json_data["reference_id"] = get_text_element(root, "relConds/condition0/gradeId")
        elif json_data["unlock_type"] == "PARTNER":
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/partnerId/id"))
        elif json_data["unlock_type"] == "MUSIC_GENRE_SELECTED":
            json_data["reference_id"] = int(get_text_element(root, "relConds/condition0/musicGenreId/id"))
        json_data["param"] = int(get_text_element(root, "relConds/condition0/param"))

        try:
            json_data["normText"] = get_text_element(root, "normText")
        except Exception:
            json_data["normText"] = ""
        json_data["rareType"] = rare_type_map.get(get_text_element(root, "rareType"), 0)

    return json_data
