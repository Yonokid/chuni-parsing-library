import xml.etree.ElementTree as ET

from chuni.utils import get_text_element, get_ref, safe_find


def parse_mapArea(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        if root.find("mapBonusName") is not None:  # older versions have no area bonus
            json_data["mapBonus"] = get_ref(root, "mapBonusName")
        if root.find("mapAreaBoostType") is not None:  # 1.45+
            json_data["boostType"] = int(get_text_element(root, "mapAreaBoostType"))
            json_data["boostMultiple"] = int(get_text_element(root, "mapAreaBoostMultiple"))  # percent
        json_data["grids"] = []
        grids = safe_find(root, "grids")
        for grid in grids.iter("MapAreaGridData"):
            grid_element = dict()
            grid_element["index"] = int(get_text_element(grid, "index"))
            grid_element["displayType"] = int(get_text_element(grid, "displayType"))
            grid_element["type"] = int(get_text_element(grid, "type"))
            if grid.find("reward") is not None:  # 1.10+: grids point at a reward
                grid_element["reward"] = get_ref(grid, "reward/rewardName")
            else:
                grid_element["gamePoint"] = int(get_text_element(grid, "gamePoint/point"))
                grid_element["ticket"] = get_ref(grid, "ticket/ticketName")
            json_data["grids"].append(grid_element)

    return json_data
