import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

from wannacri.wannacri import Usm

from chuni.utils import get_text_element


def parse_movie(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["filename"] = get_text_element(root, "usmFile/path")

    return json_data

def copy_movie(input: str, movie, output: str) -> str:
    subprocess.run(["wannacri", "extractusm", f"{input}"])
    extracted_path = os.path.join("output", movie["filename"])
    audio_file = ''
    video_file = ''
    for file in os.listdir(os.path.join(extracted_path, "audios")):
        audio_file = file
    for file in os.listdir(os.path.join(extracted_path, "videos")):
        video_file = file
    # named after the .usm, not the title: Japanese filenames get mangled by FTP/server tooling
    movie["mp4name"] = os.path.splitext(movie["filename"])[0] + ".mp4"
    subprocess.run(["ffmpeg", "-y", "-i", os.path.join(extracted_path, "audios", audio_file), "-i", os.path.join(extracted_path, "videos", video_file), os.path.join(output, movie["mp4name"])])
    shutil.rmtree(extracted_path)
    return movie
