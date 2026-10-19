import os
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_bool, get_int, get_ref, get_text_element, get_version


def parse_mate(file: str) -> dict:
    """Mate.xml (2.50+): a home-screen E-mote companion with level rewards and voiced actions."""
    root = ET.parse(file).getroot()
    json_data = {
        "id": get_int(root, "name/id"),
        "version": get_version(root),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "defaultHave": get_bool(root, "defaultHave"),
        "emoteFile": get_text_element(root, "emoteFile/path"),
        "imageFile": get_text_element(root, "image/path"),
        "chara": get_ref(root, "chara"),
        "ddsIllust": get_ref(root, "ddsIllust"),
        **{k: get_int(root, k) for k in ("systemVoiceId", "texSizeX", "texSizeY", "posX", "posY", "scaleX10000")},
    }
    json_data["rewards"] = [{"id": get_int(r, "mateRewardId"), "level": get_int(r, "level"), "reward": get_ref(r, "reward")}
                            for r in root.findall("rewards/MateRewardData")]
    json_data["actions"] = [{
        "id": get_int(a, "mateActionId"), "actionType": get_int(a, "actionType"), "emote": get_text_element(a, "emote"),
        **{k: get_bool(a, k) for k in ("isVoice", "isLipSync", "isSpecialMotion", "isEmoteEndReset")},
        **{k: get_int(a, k) for k in ("msecEmoteEnd", "cueId")}, "lipSync": get_text_element(a, "lipSync/path"),
    } for a in root.findall("actions/MateActionData")]
    return json_data


def copy_mate_image(input: str, mate: dict, output: str) -> None:
    img = Image.open(os.path.join(input, mate["imageFile"]))
    mate["image"] = f"{os.path.splitext(mate['imageFile'])[0]}.webp"
    img.save(os.path.join(output, mate["image"]))
