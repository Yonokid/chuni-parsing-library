import json
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from chuni.tables.avatarAccessory import copy_avatarAccessory_image, parse_avatarAccessory
from chuni.tables.avatarAccessoryGacha import parse_avatarAccessoryGacha
from chuni.tables.battleRatingRange import parse_battleRatingRange
from chuni.tables.battleEvent import parse_battleEvent
from chuni.tables.charaWorks import parse_charaWorks
from chuni.tables.playReward import parse_playReward, parse_playRewardSet
from chuni.tables.battleReward import parse_battleReward
from chuni.tables.dailyBonus import parse_dailyBonus, parse_dailyBonusPreset
from chuni.tables.frame import copy_frame_image, parse_frame
from chuni.tables.gacha import copy_gacha_image, parse_gacha
from chuni.tables.symbolChat import parse_symbolChat
from chuni.tables.teamPresent import parse_teamPresent
from chuni.tables.teamPresentPreset import parse_teamPresentPreset
from chuni.tables.chara import copy_chara_image, parse_chara
from chuni.tables.aimeCollab import copy_aimeCollab_image, parse_aimeCollab
from chuni.tables.achievementPattern import parse_achievementPattern
from chuni.tables.chargeItem import parse_chargeItem
from chuni.tables.unlockChallenge import parse_unlockChallenge
from chuni.tables.emote import (parse_emoteChara, parse_emoteScene, parse_emoteScript, parse_emoteTimelineDiff,
                                parse_emoteTimelineMain, process_emotedata)
from chuni.tables.course import embed_course_rules, parse_course
from chuni.tables.courseRule import parse_courseRule
from chuni.tables.duel import parse_duel
from chuni.tables.duelMission import parse_duelMission
from chuni.tables.mate import copy_mate_image, parse_mate
from chuni.tables.mapIcon import copy_mapIcon_image, parse_mapIcon
from chuni.tables.systemVoice import copy_systemVoice_files, parse_systemVoice
from chuni.tables.quest import parse_quest
from chuni.tables.name_plate import copy_namePlate_image, parse_namePlate
from chuni.tables.reward import parse_reward
from chuni.enums import build_enums, has_song_name_rarity, is_2_00
from chuni.navigation import write_navigation
from chuni.tables.event import copy_ddsBanner, copy_eventBanner, parse_event
from chuni.tables.map import copy_ddsMap, embed_map_details, parse_map
from chuni.tables.mapBonus import parse_mapBonus
from chuni.tables.cmission import parse_cmission, parse_cmissionInfo
from chuni.utils import xml_name
from chuni.tables.map_area import parse_mapArea
from chuni.tables.movie import copy_movie, parse_movie
from chuni.tables.music import copy_cueFile, copy_jacket, is_worlds_end, parse_music
from chuni.tables.present import parse_present
from chuni.tables.resources import (parse_gameTable, parse_gauge, parse_iniFile,
                       parse_ranking, parse_rightsInfo)
from chuni.tables.shop import parse_shop
from chuni.tables.skill import parse_skill
from chuni.sprites import SPRITES, SPRITES_2_00, alias_ticket_banners_2_00, alias_trophy_rank_plates, export_sprites
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
    if cue and cue["id"] != song["id"] and any(is_worlds_end(c) for c in song["charts"]):
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

def _copy_job(copy_func, path: str, item: dict, out: str) -> dict:
    """Runs in a worker process: copy_func fills fields on item (textures, models...), so ship it back."""
    copy_func(path, item, out)
    return item


def sibling_options(directory: str) -> list:
    """Other Option/AXXX dirs next to this one: 2.20 maps/characters reference art shipped in a different Option."""
    parent = os.path.dirname(os.path.normpath(directory))
    if os.path.basename(parent) != "Option":
        return []
    return [os.path.join(parent, d) for d in sorted(os.listdir(parent)) if os.path.join(parent, d) != os.path.normpath(directory)]


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
        copy_func = lambda path, song, out: audio_jobs.append((song["id"], pool.submit(copy_audio, path, song, out), None))
    elif data_type in ("chara", "stage"):  # webp encode / glb export are CPU-bound: one process per item
        pool = ProcessPoolExecutor()
        copy_cpu = copy_func
        copy_func = lambda path, item, out: audio_jobs.append((item["id"], pool.submit(_copy_job, copy_cpu, path, item, out), item))
    for item in os.scandir(data_dir):
        if not item.is_dir():
            continue
        xml_path = os.path.join(data_dir, item.name, xml_name(data_type))
        try:
            parsed_data = parse_func(xml_path)
            new_data.append(parsed_data)
            id = str(parsed_data["id"])

            if data_type == "music":
                base = worlds_end_base(parsed_data)
                if base is not None and any(os.path.isdir(os.path.join(d, "music", f"music{base:04d}")) for d in (directory, alt_dir) if d):
                    continue  # merged into the base song, which brings the audio and jacket
                cue_id = str(parsed_data["cueFile"]["id"]) if parsed_data["cueFile"] else id
                # the cue can ship in another Option than the song's XML (2.30: music2743, 8299)
                name = f"{related_dir_name}{cue_id.zfill(6)}"
                candidates = [os.path.join(d, related_dir_name, name) for d in (directory, alt_dir, *sibling_options(directory)) if d is not None]
                path = next((c for c in candidates if os.path.exists(c)), None)
                if path is not None:
                    copy_func(path, parsed_data, data_output_dir)
                elif alt_dir is not None:  # missing everywhere: copy_func reports it
                    copy_func(candidates[1], parsed_data, data_output_dir)
                path = os.path.join(directory, data_type, f"{data_type}{id.zfill(4)}")
                copy_jacket(path, parsed_data, data_output_dir)
            elif data_type == "chara":
                path = os.path.join(directory, related_dir_name, f"{related_dir_name}{id.zfill(6)}")
                if os.path.exists(path):
                    copy_func(path, parsed_data, data_output_dir)
                else:
                    name = f"{related_dir_name}{id.zfill(6)}"
                    dirs = [d for d in (alt_dir, *sibling_options(directory)) if d is not None]
                    candidates = [os.path.join(d, related_dir_name, name) for d in dirs]
                    if candidates:  # none existing: copy_func reports the first as missing
                        path = next((c for c in candidates if os.path.exists(c)), candidates[0])
                        copy_func(path, parsed_data, data_output_dir)
            elif data_type in ("namePlate", "aimeCollab", "mapIcon", "systemVoice", "avatarAccessory", "frame", "gacha", "mate"):
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
                name = f"{related_dir_name}{parsed_data["ddsMapId"].zfill(8)}"
                # Option dirs spell the folder "ddsmap" (1.45), which matters on case-sensitive filesystems
                candidates = [os.path.join(d, folder, name) for d in (directory, alt_dir, *sibling_options(directory)) if d is not None for folder in (related_dir_name, related_dir_name.lower())]
                path = next((c for c in candidates if os.path.exists(c)), candidates[-1])
                copy_func(path, parsed_data, data_output_dir)
            elif data_type == "stage":
                path = os.path.join(directory, data_type, item.name)
                copy_func(path, parsed_data, data_output_dir)

        except (FileNotFoundError, IOError, ValueError) as e:
            print(f"Error processing {data_type} {item.name}: {e}")

    for song_id, job, item in audio_jobs:
        try:
            result = job.result()
            if item is not None:
                item.update(result)
        except (FileNotFoundError, IOError, ValueError) as e:
            print(f"Error processing {data_type} {song_id}: {e}")
    pool.shutdown()

    if data_type == "music":  # a re-parsed song must keep the WORLD'S END charts already folded into it
        old_by_id = {s["id"]: s for s in existing_data}
        for song in new_data:
            have = {c.get("worldsEndId") for c in song["charts"]}
            song["charts"] += [c for c in old_by_id.get(song["id"], {}).get("charts", []) if c.get("worldsEndId") not in have | {None}]
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
    process_data(directory, alt_dir, output_dir, "achievementPattern", parse_achievementPattern, None, "achievementPattern")
    process_data(directory, alt_dir, output_dir, "reward", parse_reward, None, "reward")
    process_data(directory, alt_dir, output_dir, "present", parse_present, None, "present")
    process_data(directory, alt_dir, output_dir, "stage", parse_stage, copy_stage_files, "stage")
    process_data(directory, alt_dir, output_dir, "event", parse_event, copy_ddsBanner, "ddsBanner")
    process_data(directory, alt_dir, output_dir, "map", parse_map, copy_ddsMap, "ddsMap")
    process_data(directory, alt_dir, output_dir, "shop", parse_shop, None, "shop")
    process_data(directory, alt_dir, output_dir, "mapArea", parse_mapArea, None, "mapArea")
    process_data(directory, alt_dir, output_dir, "mapBonus", parse_mapBonus, None, "mapBonus")
    process_data(directory, alt_dir, output_dir, "cmission", parse_cmission, None, "cmission")
    process_data(directory, alt_dir, output_dir, "cmissionInfo", parse_cmissionInfo, None, "cmissionInfo")
    process_data(directory, alt_dir, output_dir, "unlockChallenge", parse_unlockChallenge, None, "unlockChallenge")
    for emote_type, emote_parse in (("emoteChara", parse_emoteChara), ("emoteScene", parse_emoteScene), ("emoteScript", parse_emoteScript),
                                    ("emoteTimelineMain", parse_emoteTimelineMain), ("emoteTimelineDiff", parse_emoteTimelineDiff)):
        process_data(directory, alt_dir, output_dir, emote_type, emote_parse, None, emote_type)
    process_emotedata(directory, output_dir)
    process_data(directory, alt_dir, output_dir, "aimeCollab", parse_aimeCollab, copy_aimeCollab_image, "aimeCollab")
    process_data(directory, alt_dir, output_dir, "course", parse_course, None, "course")
    process_data(directory, alt_dir, output_dir, "courseRule", parse_courseRule, None, "courseRule")
    process_data(directory, alt_dir, output_dir, "duel", parse_duel, None, "duel")
    process_data(directory, alt_dir, output_dir, "duelMission", parse_duelMission, None, "duelMission")
    process_data(directory, alt_dir, output_dir, "mapIcon", parse_mapIcon, copy_mapIcon_image, "mapIcon")
    process_data(directory, alt_dir, output_dir, "mate", parse_mate, copy_mate_image, "mate")
    process_data(directory, alt_dir, output_dir, "systemVoice", parse_systemVoice, copy_systemVoice_files, "systemVoice")
    process_data(directory, alt_dir, output_dir, "quest", parse_quest, None, "quest")
    process_data(directory, alt_dir, output_dir, "namePlate", parse_namePlate, copy_namePlate_image, "namePlate")
    process_data(directory, alt_dir, output_dir, "avatarAccessory", parse_avatarAccessory, copy_avatarAccessory_image, "avatarAccessory")
    process_data(directory, alt_dir, output_dir, "avatarAccessoryGacha", parse_avatarAccessoryGacha, None, "avatarAccessoryGacha")
    process_data(directory, alt_dir, output_dir, "frame", parse_frame, copy_frame_image, "frame")
    process_data(directory, alt_dir, output_dir, "symbolChat", parse_symbolChat, None, "symbolChat")
    process_data(directory, alt_dir, output_dir, "battleReward", parse_battleReward, None, "battleReward")
    process_data(directory, alt_dir, output_dir, "battleRatingRange", parse_battleRatingRange, None, "battleRatingRange")
    process_data(directory, alt_dir, output_dir, "battleEvent", parse_battleEvent, None, "battleEvent")
    process_data(directory, alt_dir, output_dir, "charaWorks", parse_charaWorks, None, "charaWorks")
    process_data(directory, alt_dir, output_dir, "playReward", parse_playReward, None, "playReward")
    process_data(directory, alt_dir, output_dir, "playRewardSet", parse_playRewardSet, None, "playRewardSet")
    process_data(directory, alt_dir, output_dir, "dailyBonus", parse_dailyBonus, None, "dailyBonus")
    process_data(directory, alt_dir, output_dir, "dailyBonusPreset", parse_dailyBonusPreset, None, "dailyBonusPreset")
    process_data(directory, alt_dir, output_dir, "gacha", parse_gacha, copy_gacha_image, "gacha")
    process_data(directory, alt_dir, output_dir, "teamPresent", parse_teamPresent, None, "teamPresent")
    process_data(directory, alt_dir, output_dir, "teamPresentPreset", parse_teamPresentPreset, None, "teamPresentPreset")
    db_dir = os.path.join(os.path.dirname(os.path.normpath(alt_dir or directory)), "db")
    if os.path.isdir(db_dir):
        ensure_directory(output_dir)
        with open(os.path.join(output_dir, "enums.json"), "w", encoding="utf-8") as f:
            json.dump(build_enums(db_dir, output_dir), f, indent=4, ensure_ascii=False)
    texture_dir = os.path.join(os.path.dirname(db_dir), "surfboard", "texture")
    if os.path.isdir(texture_dir):
        export_sprites(texture_dir, os.path.join(output_dir, "sprites"), {**SPRITES, **SPRITES_2_00} if is_2_00(output_dir) else SPRITES)
        if has_song_name_rarity(output_dir):
            alias_trophy_rank_plates(os.path.join(output_dir, "sprites"))
        if is_2_00(output_dir):
            alias_ticket_banners_2_00(os.path.join(output_dir, "sprites"))
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
    embed_map_details(output_dir)
    embed_course_rules(output_dir)
    write_navigation(output_dir)
