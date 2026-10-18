import io
import os
import shutil
import xml.etree.ElementTree as ET

from PIL import Image

from chuni.stage3d.afb import AcroReader, AFRC_Reader, extract_svo_textures
from chuni.utils import get_text_element
from chuni.stage3d.export import export_stage


def parse_stage(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = int(get_text_element(root, "resourceVersion/str"))
        json_data["name"] = get_text_element(root, "name/str")
        json_data["releaseTagName"] = get_text_element(root, "releaseTagName/str")
        json_data["notesFieldLine"] = get_text_element(root, "notesFieldLine/str")
        json_data["notesFieldFile"] = get_text_element(root, "notesFieldFile/path")
        json_data["baseFile"] = get_text_element(root, "baseFile/path")
        json_data["objectFile"] = get_text_element(root, "objectFile/path")

    return json_data

def _extract_afb_textures(afb_path: str, output: str) -> list[str]:
    """Unpacks a .afb (FILS container) and converts any embedded .dds textures to .webp."""
    try:
        acro = AcroReader(open(afb_path, "rb"))
        files, _names = acro.read_file_system()
        if len(files) != 2:
            return []
        afrc_files = AFRC_Reader(files[1]).read_afrc()
    except (AssertionError, IndexError, ValueError):
        return []

    webp_names = []
    for entry in afrc_files:
        name_lower = entry.name.lower()
        if name_lower.endswith(".dds"):
            dds_blobs = [(entry.name, entry.content.read(entry.length))]
        elif name_lower.endswith(".svo"):
            dds_blobs = extract_svo_textures(entry.content.read(entry.length))
        else:
            continue

        for dds_name, dds_data in dds_blobs:
            webp_name = os.path.splitext(os.path.basename(dds_name))[0] + ".webp"
            try:
                img = Image.open(io.BytesIO(dds_data))
                img.save(os.path.join(output, webp_name))
            except Exception:
                continue
            webp_names.append(webp_name)

    return webp_names

def copy_stage_files(input: str, stage: dict, output: str) -> None:
    textures, models = [], []
    for key in ("notesFieldFile", "baseFile", "objectFile"):
        filename = stage.get(key)
        if not filename:
            continue
        src = os.path.join(input, filename)
        if not os.path.isfile(src):
            continue
        if not filename.lower().endswith(".afb"):  # .afb sources aren't published, only the .glb
            shutil.copy(src, os.path.join(output, filename))
        else:
            textures.extend(_extract_afb_textures(src, output))
            glb = os.path.splitext(filename)[0] + ".glb"
            try:
                if export_stage(src, os.path.join(output, glb)):
                    models.append(glb)
            except Exception as e:
                print(f"stage3d: {filename}: {e!r}")

    stage["textures"] = textures
    stage["models"] = models
