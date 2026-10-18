import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import (get_version, get_bool, get_int, get_ref, get_text_element,
                          line_break, parse_conditions, safe_find)


def parse_chara(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["rightsInfoName"] = root.findtext("rightsInfoName/str", "Invalid")  # dropped in 2.00
        json_data["sortName"] = get_text_element(root, "sortName")
        json_data["works"] = get_text_element(root, "works/str")
        json_data["illustratorName"] = get_text_element(root, "illustratorName/str")
        json_data["firstSkill"] = root.findtext("firstSkill/str")  # dropped in 2.00 (ranks hand out skill seeds instead)
        json_data["skillId"] = root.findtext("firstSkill/id")
        json_data["rareType"] = int(get_text_element(root, "rareType"))
        json_data["releaseTagName"] = get_text_element(root, "releaseTagName/str")
        json_data["explainText"] = line_break(root.findtext("explainText"))  # optional: game keeps default when absent
        json_data["defaultHave"] = get_bool(root, "defaultHave")
        json_data["defaultImage"] = get_ref(root, "defaultImages")
        json_data["priority"] = get_int(root, "priority")
        json_data["conditions"] = parse_conditions(root)

        add_images = []
        for i in range(1, 10):  # 3 before 2.00
            tag = f"addImages{i}"
            if root.find(tag) is None:
                continue
            add_image_el = safe_find(root, tag)
            if get_text_element(add_image_el, "changeImg") != "true":
                continue
            chara_ref = get_ref(add_image_el, "charaName")
            if chara_ref:
                chara_ref["image"] = get_ref(add_image_el, "image")
                if add_image_el.find("rank") is not None:  # 2.00+: chara rank that unlocks the image
                    chara_ref["rank"] = get_int(add_image_el, "rank")
                add_images.append(chara_ref)
        json_data["addImages"] = add_images

        ranks = []
        for rank in safe_find(root, "ranks").iter("CharaRankData"):
            rank_data = dict()
            rank_data["index"] = int(get_text_element(rank, "index"))
            rank_data["type"] = get_int(rank, "type")
            skill_id = int(rank.findtext("skill/skill/id", "-1"))
            if skill_id > 0:
                rank_data["skill"] = {
                    "id": skill_id,
                    "name": get_text_element(rank, "skill/skill/str"),
                }
            seed = get_ref(rank, "rewardSkillSeed/rewardSkillSeed")  # 2.00+
            if seed:
                rank_data["skillSeed"] = seed
            flavor_path = get_text_element(rank, "text/flavorTxtFile/path")
            if flavor_path:
                full_path = os.path.join(os.path.dirname(file), flavor_path)
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as flavor:
                        rank_data["flavorText"] = "".join(flavor.readlines())
            ranks.append(rank_data)
        json_data["ranks"] = ranks

        i = 1
        flavor_text = []
        while os.path.exists(os.path.join(os.path.dirname(file), f'flavor{str(json_data["id"]).zfill(6)}_0{i}.rom.txt')):
            with open(os.path.join(os.path.dirname(file), f'flavor{str(json_data["id"]).zfill(6)}_0{i}.rom.txt'), "r", encoding="utf-8") as flavor:
                flavor_text.append(''.join(flavor.readlines()))
            i += 1
        json_data["flavorText"] = flavor_text

    return json_data

def copy_chara_image(input: str, chara, output: str) -> None:
    img = Image.open(os.path.join(input, f'CHU_UI_Character_{str(chara["id"]).zfill(5)[:-1]}_00_00.dds'))
    img.save(os.path.join(output, f'CHU_UI_Character_{str(chara["id"]).zfill(5)[:-1]}_00_00.webp'))
    img = Image.open(os.path.join(input, f'CHU_UI_Character_{str(chara["id"]).zfill(5)[:-1]}_00_01.dds'))
    img.save(os.path.join(output, f'CHU_UI_Character_{str(chara["id"]).zfill(5)[:-1]}_00_01.webp'))
    img = Image.open(os.path.join(input, f'CHU_UI_Character_{str(chara["id"]).zfill(5)[:-1]}_00_02.dds'))
    img.save(os.path.join(output, f'CHU_UI_Character_{str(chara["id"]).zfill(5)[:-1]}_00_02.webp'))
