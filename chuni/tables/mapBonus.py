import xml.etree.ElementTree as ET

from chuni.utils import get_ref, get_text_element, get_version, safe_find

# substance <type> picks which child block applies; order matches the type ids 0..9 (checked against the data)
KINDS = ("chara", "charaWorks", "skill", "skillCategory", "music", "musicGenre", "musicWorks", "musicDif", "musicLv", "charaRank")


def parse_mapBonus(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["substances"] = []
        for sub in safe_find(root, "substances/list").iter("MapBonusSubstanceData"):
            kind_id = int(get_text_element(sub, "type"))
            kind = KINDS[kind_id]
            block = safe_find(sub, kind)
            # the block's one StringID child (charaName, genreName, filterLv...) is what the bonus applies to
            if kind == "charaRank":  # 2.20: target is a plain min rank, not a ref
                target = {"id": int(get_text_element(block, "charaRank")), "name": block.findtext("explainText") or ""}
            else:
                child = next(c for c in block if c.find("id") is not None and c.tag != "resourceVersion")
                target = get_ref(block, child.tag)
            json_data["substances"].append({
                "type": kind_id,
                "kind": kind,
                "point": int(get_text_element(block, "point")),
                "target": target,
            })

    return json_data
