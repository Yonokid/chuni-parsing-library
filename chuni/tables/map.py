import json
import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_bool, get_int, get_ref, get_text_element, get_version, safe_find


def parse_map(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["ddsMapId"] = get_text_element(root, "infos/MapDataAreaInfo/ddsMapName/id")
        json_data["mapType"] = get_int(root, "mapType")
        if root.find("mapFilterID") is not None:  # 1.20.00+
            json_data["mapFilter"] = get_ref(root, "mapFilterID")
        if root.find("netDispPeriod") is not None:
            json_data["netDispPeriod"] = get_bool(root, "netDispPeriod")
        json_data["stopMapArea"] = get_ref(root, "stopMapAreaName")
        json_data["stopUnlockEvent"] = get_ref(root, "stopUnlockEventName")
        if root.find("categoryName") is not None:  # 2.00+: pages of areas, stop gates on a page / release event instead
            json_data["category"] = get_ref(root, "categoryName")
            json_data["stopPageIndex"] = get_int(root, "stopPageIndex")
            json_data["stopReleaseEvent"] = get_ref(root, "stopReleaseEventName")

        areas = []
        for info in safe_find(root, "infos").iter("MapDataAreaInfo"):
            # 1.10+ replaced chara/skill/trophy with a single reward
            area = {
                key: get_ref(info, f"{key}Name") if info.find(f"{key}Name") is not None else None
                for key in ("mapArea", "ddsMap", "music", "reward", "chara", "skill", "trophy", "normalGauge", "challengeGauge")
            }
            if info.find("challengeRating") is not None:  # dropped in 2.00
                area["challengeRating"] = {
                    dif: get_int(info, f"challengeRating/{dif}") for dif in ("advanced", "expert", "master")
                }
            if info.find("gaugeName") is not None:  # 2.00+: one gauge replaces normal/challenge
                area["gauge"] = get_ref(info, "gaugeName")
                for key in ("pageIndex", "indexInPage", "requiredAchievementCount"):
                    area[key] = get_int(info, key)
            areas.append(area)
        json_data["areas"] = areas

    return json_data

def copy_ddsMap(input: str, event: dict, output: str) -> None:
    files = os.listdir(input)
    dds_files = [f for f in files if f.endswith('.dds')]
    filename = os.path.splitext(dds_files[0])[0]
    img = Image.open(os.path.join(input, dds_files[0]))
    event["ddsMapName"] = f"{filename}.webp"
    img.save(os.path.join(output, f"{filename}.webp"))

def embed_map_details(output_dir: str) -> None:
    """Inlines each area's tiles (mapArea.json) with full rewards, and tile bonus (mapBonus.json), into map.json: they only make sense as part of a map."""
    def load(name):
        path = os.path.join(output_dir, name, f"{name}.json")
        if not os.path.exists(path):
            return None, {}
        with open(path, "r", encoding="utf-8") as f:
            return path, {item["id"]: item for item in json.load(f)}

    map_path, _ = load("map")
    if map_path is None:
        return
    _, areas = load("mapArea")
    _, bonuses = load("mapBonus")
    _, gauges = load("gauge")
    _, rewards = load("reward")

    _, skills = load("skill")
    _, plates = load("namePlate")
    _, tickets = load("ticket")

    def icon(reward):
        path = icon_path(reward)
        return path if path and os.path.exists(os.path.join(output_dir, path)) else None  # e.g. ticket types without a banner

    def icon_path(reward):
        """Image path (relative to the version folder) for a non-chara reward, if it has one."""
        skill = reward["skill"] or reward.get("skillSeed")  # 2.00: skills are granted as seeds
        if skill and skill["id"] in skills:
            return f"sprites/skillCategory_{skills[skill['id']]['category']}.webp"
        if reward["namePlate"] and reward["namePlate"]["id"] in plates:
            return f"namePlate/{plates[reward['namePlate']['id']]['image']}"
        if reward["ticket"] and reward["ticket"]["id"] in tickets:
            return f"sprites/ticketType_{tickets[reward['ticket']['id']]['type']}.webp"

    def full_reward(ref):
        reward = rewards.get((ref or {}).get("id"))
        if not (ref and reward):
            return ref
        return {**ref, **reward, "icon": icon(reward)}
    with open(map_path, "r", encoding="utf-8") as f:
        maps = json.load(f)
    for map_ in maps:
        for info in map_["areas"]:
            area = areas.get((info["mapArea"] or {}).get("id"))
            if area is None:
                continue
            for key in ("normalGauge", "challengeGauge", "gauge"):  # per-difficulty norma/max, see gauge.md
                gauge = gauges.get((info.get(key) or {}).get("id"))
                if gauge:
                    info[key] = {**info[key], "fumens": gauge["fumens"]}
            info["reward"] = full_reward(info["reward"])
            info["grids"] = [{**grid, "reward": full_reward(grid.get("reward"))} if "reward" in grid else grid for grid in area["grids"]]
            bonus = bonuses.get((area.get("mapBonus") or {}).get("id"))
            info["bonus"] = bonus and {"id": bonus["id"], "name": bonus["name"], "substances": bonus["substances"]}
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(maps, f, indent=4, ensure_ascii=False)
