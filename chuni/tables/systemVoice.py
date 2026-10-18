import os
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.utils import get_bool, get_int, get_ref, get_text_element


def parse_systemVoice(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        root = ET.parse(xml_file).getroot()

    return {
        "id": int(get_text_element(root, "name/id")),
        "version": int(get_text_element(root, "resourceVersion/str")),
        "name": get_text_element(root, "name/str"),
        "disableFlag": get_bool(root, "disableFlag"),
        "works": get_ref(root, "works"),
        "cue": get_ref(root, "cue"),  # cueFile/cueFile<id:06>/<name>.awb
        "explainText": get_text_element(root, "explainText"),
        "defaultHave": get_bool(root, "defaultHave"),
        "priority": get_int(root, "priority"),
        "imageFile": get_text_element(root, "image/path"),
    }

def copy_systemVoice_files(input: str, voice: dict, output: str) -> None:
    img = Image.open(os.path.join(input, voice["imageFile"]))
    voice["image"] = f"{os.path.splitext(voice['imageFile'])[0]}.webp"
    img.save(os.path.join(output, voice["image"]))
    cue = voice["cue"]
    awb = os.path.join(os.path.dirname(os.path.dirname(input)), "cueFile", f"cueFile{cue['id']:06d}", f"{cue['name']}.awb")
    if not os.path.exists(awb):  # cue shipped by another Option folder: no audio
        return
    mp3 = os.path.join(output, f"{cue['name']}.mp3")
    wav = os.path.join(output, f"{cue['name']}.wav")
    subprocess.run(["vgmstream-cli", awb, "-o", wav])
    subprocess.run(["ffmpeg", "-y", "-i", wav, mp3])
    os.remove(wav)
    voice["audio"] = f"{cue['name']}.mp3"
