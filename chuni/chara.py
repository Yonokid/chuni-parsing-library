import os
import xml.etree.ElementTree as ET

from PIL import Image

from global_utils import get_text_element, safe_find


def parse_chara(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["rightsInfoName"] = get_text_element(root, "rightsInfoName/str")
        json_data["sortName"] = get_text_element(root, "sortName")
        json_data["works"] = get_text_element(root, "works/str")
        json_data["illustratorName"] = get_text_element(root, "illustratorName/str")
        json_data["firstSkill"] = get_text_element(root, "firstSkill/str")
        json_data["skillId"] = get_text_element(root, "firstSkill/id")
        addImages = []
        i = 0
        while root.find(f"addImages{i}") is not None:
            addImage = safe_find(root, f"addImages{i}")
            data_dict = dict()
            data_dict["charaName"] = get_text_element(addImage, "charaName/str")
            addImages.append(data_dict)
            i += 1
        json_data["addImages"] = addImages
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
