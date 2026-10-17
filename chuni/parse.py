import json
import os
from concurrent.futures import ThreadPoolExecutor

from chuni.tables.chara import copy_chara_image, parse_chara
from chuni.tables.chargeItem import parse_chargeItem
from chuni.tables.course import parse_course
from chuni.tables.name_plate import copy_namePlate_image, parse_namePlate
from chuni.tables.reward import parse_reward
from chuni.enums import build_enums
from chuni.navigation import write_navigation
from chuni.tables.event import copy_ddsBanner, copy_eventBanner, parse_event
from chuni.tables.map import copy_ddsMap, parse_map
from chuni.tables.map_area import parse_mapArea
from chuni.tables.movie import copy_movie, parse_movie
from chuni.tables.music import copy_cueFile, copy_jacket, parse_music
from chuni.tables.present import parse_present
from chuni.tables.resources import (parse_gameTable, parse_gauge, parse_iniFile,
                       parse_ranking, parse_rightsInfo)
from chuni.tables.shop import parse_shop
from chuni.tables.skill import parse_skill
from chuni.sprites import export_sprites
from chuni.tables.stage import copy_stage_files, parse_stage
from chuni.tables.ticket import parse_ticket
from chuni.tables.trophy import parse_trophy


def ensure_directory(path: str) -> None:
    """Ensures that the given directory exists."""
    if not os.path.isdir(path):
        os.makedirs(path)

def combine_unique_keys(list1, list2, unique_key):
    combined_dict = {}
    for d in list1 + list2:
        combined_dict[d[unique_key]] = d
    return list(combined_dict.values())

def worlds_end_base(song: dict) -> int | None:
    """WORLD'S END charts are separate 8xxx songs reusing their base song's audio: that song's id."""
    cue = song["cueFile"]
    if cue and cue["id"] != song["id"] and any(c["difficulty"] == 4 for c in song["charts"]):
        return cue["id"]
    return None

def merge_worlds_end(songs: list) -> list:
    """Folds each WORLD'S END song into its base song as one more chart (kept standalone if the base is missing)."""
    by_id = {s["id"]: s for s in songs}
    for song in list(songs):
        base = by_id.get(worlds_end_base(song))
        if base is None:
            continue
        for chart in song["charts"]:
            chart["worldsEndId"] = song["id"]
            base["charts"] = [c for c in base["charts"] if c.get("worldsEndId") != song["id"]] + [chart]
        songs.remove(song)
    return songs

def process_data(directory: str, alt_dir, output_dir: str, data_type: str, parse_func, copy_func, related_dir_name: str) -> None:
    """
    Processes data (music, chara, movie) from the given directory.

    Args:
        directory: The input directory.
        output_dir: The base output directory.
        data_type: The type of data ("music", "chara", "movie").
        parse_func: The function to parse the XML file.
        copy_func: The function to copy related files.
        related_dir_name: The name of the related directory/file.
        id_extraction_func: Function to extract the id used for related files, if needed.
    """
    data_dir = os.path.join(directory, data_type)
    if not os.path.exists(data_dir):
        print(f"Directory {data_type} does not exist, skipping")
        return
    data_output_dir = os.path.join(output_dir, data_type)
    ensure_directory(data_output_dir)

    json_file_path = os.path.join(data_output_dir, f"{data_type}.json")
    existing_data = []

    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading existing {data_type}.json: {e}. Starting with an empty list.")
            existing_data = []

    new_data = []
    pool = ThreadPoolExecutor()
    audio_jobs = []
    if data_type == "music":  # vgmstream/ffmpeg dominate runtime: run them concurrently, errors reported below
        copy_audio = copy_func
        copy_func = lambda path, song, out: audio_jobs.append((song["id"], pool.submit(copy_audio, path, song, out)))
    for item in os.scandir(data_dir):
        if not item.is_dir():
            continue
        xml_path = os.path.join(data_dir, item.name, f"{data_type[0].upper()}{data_type[1:]}.xml")
        try:
            parsed_data = parse_func(xml_path)
            new_data.append(parsed_data)
            id = str(parsed_data["id"])

            if data_type == "music":
                base = worlds_end_base(parsed_data)
                if base is not None and any(os.path.isdir(os.path.join(d, "music", f"music{base:04d}")) for d in (directory, alt_dir) if d):
                    continue  # merged into the base song, which brings the audio and jacket
                cue_id = str(parsed_data["cueFile"]["id"]) if parsed_data["cueFile"] else id
                path = os.path.join(directory, related_dir_name, f"{related_dir_name}{cue_id.zfill(6)}")
                if os.path.exists(path):
                    copy_func(path, parsed_data, data_output_dir)
                elif alt_dir is not None:
                    path = os.path.join(alt_dir, related_dir_name, f"{related_dir_name}{cue_id.zfill(6)}")
                    copy_func(path, parsed_data, data_output_dir)
                path = os.path.join(directory, data_type, f"{data_type}{id.zfill(4)}")
                copy_jacket(path, parsed_data, data_output_dir)
            elif data_type == "chara":
                path = os.path.join(directory, related_dir_name, f"{related_dir_name}{id.zfill(6)}")
                if os.path.exists(path):
                    copy_func(path, parsed_data, data_output_dir)
                elif alt_dir is not None:
                    path = os.path.join(alt_dir, related_dir_name, f"{related_dir_name}{id.zfill(6)}")
                    copy_func(path, parsed_data, data_output_dir)
            elif data_type == "namePlate":
                path = os.path.join(directory, data_type, item.name)
                copy_func(path, parsed_data, data_output_dir)
            elif data_type == "movie":
                path = os.path.join(directory, related_dir_name, f"{related_dir_name}{id.zfill(6)}", parsed_data["filename"])
                if os.path.exists(path):
                    copy_func(path, parsed_data, data_output_dir)
                elif alt_dir is not None:
                    path = os.path.join(alt_dir, related_dir_name, f"{related_dir_name}{id.zfill(6)}", parsed_data["filename"])
                    copy_func(path, parsed_data, data_output_dir)
            elif data_type == "event":
                path = os.path.join(directory, data_type, f"{data_type}{id.zfill(8)}", parsed_data["eventBannerName"])
                banner_path = os.path.join(directory, related_dir_name, f"{related_dir_name}{parsed_data["ddsBannerId"].zfill(8)}")
                if os.path.isfile(path):
                    copy_eventBanner(os.path.join(directory, data_type, f"{data_type}{id.zfill(8)}"), parsed_data, data_output_dir)
                if parsed_data["ddsBannerId"] == "-1":  # no banner
                    pass
                elif os.path.exists(banner_path):
                    copy_func(banner_path, parsed_data, data_output_dir)
                elif alt_dir is not None:
                    banner_path = os.path.join(alt_dir, related_dir_name, f"{related_dir_name}{parsed_data["ddsBannerId"].zfill(8)}")
                    copy_func(banner_path, parsed_data, data_output_dir)
            elif data_type == "map":
                path = os.path.join(directory, related_dir_name, f"{related_dir_name}{parsed_data["ddsMapId"].zfill(8)}")
                if os.path.exists(path):
                    copy_func(path, parsed_data, data_output_dir)
                elif alt_dir is not None:
                    path = os.path.join(alt_dir, related_dir_name, f"{related_dir_name}{parsed_data["ddsMapId"].zfill(8)}")
                    copy_func(path, parsed_data, data_output_dir)
            elif data_type == "stage":
                path = os.path.join(directory, data_type, item.name)
                copy_func(path, parsed_data, data_output_dir)

        except (FileNotFoundError, IOError, ValueError) as e:
            print(f"Error processing {data_type} {item.name}: {e}")

    for song_id, job in audio_jobs:
        try:
            job.result()
        except (FileNotFoundError, IOError, ValueError) as e:
            print(f"Error processing {data_type} {song_id}: {e}")
    pool.shutdown()

    combined_data = combine_unique_keys(existing_data, new_data, "id")
    if data_type == "music":
        combined_data = merge_worlds_end(combined_data)

    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=4, ensure_ascii=False)

def parse_AXXX_directory(directory: str, output_dir: str, alt_dir=None) -> None:
    """Parses AXXX directory, processing music, chara, and movie data."""
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return

    process_data(directory, alt_dir, output_dir, "music", parse_music, copy_cueFile, "cueFile")
    process_data(directory, alt_dir, output_dir, "chara", parse_chara, copy_chara_image, "ddsImage")
    process_data(directory, alt_dir, output_dir, "movie", parse_movie, copy_movie, "movie")
    process_data(directory, alt_dir, output_dir, "skill", parse_skill, None, "skill")
    process_data(directory, alt_dir, output_dir, "trophy", parse_trophy, None, "trophy")
    process_data(directory, alt_dir, output_dir, "ticket", parse_ticket, None, "ticket")
    process_data(directory, alt_dir, output_dir, "chargeItem", parse_chargeItem, None, "chargeItem")
    process_data(directory, alt_dir, output_dir, "reward", parse_reward, None, "reward")
    process_data(directory, alt_dir, output_dir, "present", parse_present, None, "present")
    process_data(directory, alt_dir, output_dir, "stage", parse_stage, copy_stage_files, "stage")
    process_data(directory, alt_dir, output_dir, "event", parse_event, copy_ddsBanner, "ddsBanner")
    process_data(directory, alt_dir, output_dir, "map", parse_map, copy_ddsMap, "ddsMap")
    process_data(directory, alt_dir, output_dir, "shop", parse_shop, None, "shop")
    process_data(directory, alt_dir, output_dir, "mapArea", parse_mapArea, None, "mapArea")
    process_data(directory, alt_dir, output_dir, "course", parse_course, None, "course")
    process_data(directory, alt_dir, output_dir, "namePlate", parse_namePlate, copy_namePlate_image, "namePlate")
    db_dir = os.path.join(os.path.dirname(os.path.normpath(alt_dir or directory)), "db")
    if os.path.isdir(db_dir):
        ensure_directory(output_dir)
        with open(os.path.join(output_dir, "enums.json"), "w", encoding="utf-8") as f:
            json.dump(build_enums(db_dir), f, indent=4, ensure_ascii=False)
    texture_dir = os.path.join(os.path.dirname(db_dir), "surfboard", "texture")
    if os.path.isdir(texture_dir):
        export_sprites(texture_dir, os.path.join(output_dir, "sprites"))
    for data_type, parse_func in (
        ("iniFile", parse_iniFile), ("rightsInfo", parse_rightsInfo), ("gauge", parse_gauge),
        ("gameTable", parse_gameTable), ("ranking", parse_ranking),
    ):
        process_data(directory, alt_dir, output_dir, data_type, parse_func, None, data_type)

def process_directory(directory: str, output_dir: str, base_dir: str | None = None) -> None:
    if os.path.basename(directory.rstrip('/\\')) == "Option":
        base_dir = base_dir or os.path.join(os.path.dirname(directory.rstrip('/\\')), "App", "data", "A000")
        for folder in sorted(os.listdir(directory)):  # later options override earlier ones
            parse_AXXX_directory(os.path.join(directory, folder), output_dir, base_dir)
    else:
        parse_AXXX_directory(directory, output_dir, base_dir)
    write_navigation(output_dir)
