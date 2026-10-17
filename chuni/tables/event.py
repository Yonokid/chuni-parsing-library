import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import (get_bool, get_int, get_ref, get_ref_list,
                          get_text_element, line_break, safe_find)

# EventData.substances.type -> active sub-struct (deserializer field order; matches shipped data).
SUBSTANCES = {
    0: ("flag", lambda el: {"value": get_int(el, "value")}),
    1: ("information", lambda el: {
        "informationType": get_int(el, "informationType"),
        "text": line_break(el.findtext("text")),
        "image": get_text_element(el, "image/path"),
        "movie": get_ref(el, "movieName"),
    }),
    2: ("map", lambda el: {
        "tagText": get_text_element(el, "tagText"),
        "map": get_ref(el, "mapName"),
        "musics": get_ref_list(el, "musicNames/list"),
    }),
    3: ("music", lambda el: {"musics": get_ref_list(el, "musicNames/list")}),
    4: ("advertiseMovie", lambda el: {
        "firstMovie": get_ref(el, "firstMovieName"),
        "secondMovie": get_ref(el, "secondMovieName"),
    }),
    5: ("recommendMusic", lambda el: {"musics": get_ref_list(el, "musicNames/list")}),
}


def parse_event(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["ddsBannerId"] = get_text_element(root, "ddsBannerName/id")
        json_data["eventBannerName"] = get_text_element(root, "substances/information/image/path")
        json_data["text"] = line_break(root.findtext("text"))  # optional: game keeps default when absent
        json_data["periodDispType"] = get_int(root, "periodDispType")
        json_data["alwaysOpen"] = get_bool(root, "alwaysOpen")
        json_data["priority"] = get_int(root, "priority")

        substances = safe_find(root, "substances")
        substance_type = get_int(substances, "type")
        tag, parse = SUBSTANCES[substance_type]
        json_data["substance"] = {"type": substance_type, "kind": tag, **parse(safe_find(substances, tag))}

    return json_data

def copy_eventBanner(input: str, event: dict, output: str):
    img = Image.open(os.path.join(input, event["eventBannerName"]))
    img.save(os.path.join(output, f"{event["eventBannerName"]}.webp"))

def copy_ddsBanner(input: str, event: dict, output: str) -> None:
    files = os.listdir(input)
    dds_files = [f for f in files if f.endswith('.dds')]
    filename = os.path.splitext(dds_files[0])[0]
    img = Image.open(os.path.join(input, dds_files[0]))
    event["ddsBannerName"] = f"{filename}.webp"
    img.save(os.path.join(output, f"{filename}.webp"))
