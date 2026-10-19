import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

from wannacri.wannacri import Usm

from chuni.utils import get_text_element, get_version


def parse_movie(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["filename"] = get_text_element(root, "usmFile/path")

    return json_data

# USM key of the 2.00+ .enc movies (from the EzSFEnc encoder).
ENC_KEY = "0x0074FF1FCE264700"

def copy_movie(input: str, movie, output: str) -> str:
    key = ["-k", ENC_KEY] if movie["filename"].endswith(".enc") else []
    subprocess.run(["wannacri", "extractusm", f"{input}", *key])
    # wannacri lowercases the folder name (MOVIE_Melodiniq.enc -> movie_melodiniq.enc)
    extracted_path = os.path.join("output", next(d for d in os.listdir("output") if d.lower() == movie["filename"].lower()))
    audio_file = ''
    video_file = ''
    for file in os.listdir(os.path.join(extracted_path, "audios")):
        audio_file = file
    for file in os.listdir(os.path.join(extracted_path, "videos")):
        video_file = file
    # named after the .usm, not the title: Japanese filenames get mangled by FTP/server tooling
    mp4name = os.path.splitext(movie["filename"])[0] + ".mp4"
    result = subprocess.run(["ffmpeg", "-y", "-i", os.path.join(extracted_path, "audios", audio_file), "-i", os.path.join(extracted_path, "videos", video_file), os.path.join(output, mp4name)])
    if result.returncode == 0:  # e.g. a movie that fails to demux
        movie["mp4name"] = mp4name
    shutil.rmtree(extracted_path)
    return movie
