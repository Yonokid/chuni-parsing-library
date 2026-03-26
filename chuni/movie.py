import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

from wannacri.wannacri import Usm

from global_utils import get_text_element


def parse_movie(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = get_text_element(root, "name/id")
        json_data["version"] = get_text_element(root, "resourceVersion/str")
        json_data["name"] = get_text_element(root, "name/str")
        json_data["filename"] = get_text_element(root, "usmFile/path")

    return json_data

def copy_movie(input: str, movie, output: str) -> str:
    subprocess.run(["wannacri", "extractusm", f"{input}"])
    path = output.split('\\')[:1]
    path.append(f"\\{movie["filename"]}")
    extracted_path = ''.join(path)
    audio_file = ''
    video_file = ''
    for file in os.listdir(f"{extracted_path}\\audios"):
        audio_file = file
    for file in os.listdir(f"{extracted_path}\\videos"):
        video_file = file
    subprocess.run(["ffmpeg", "-i", f"{extracted_path}\\audios\\{audio_file}", "-i", f"{extracted_path}\\videos\\{video_file}", f"{output}\\{movie["name"]}.mp4"])
    movie["mp4name"] = movie["name"] + ".mp4"
    shutil.rmtree(extracted_path)
    return movie
