"""Cut enum sprites (trophy rank plates, skill category icons, ticket banners) out of the surfboard UI atlases.

Rects are (left, top, right, bottom) pixels from the CROP chunks of the matching .srd layouts
(common/trophyRank/CHU_UI_Character_title_rank_00_v10.srd, common/skillInfo/CHU_UI_SkillData_00_v10.srd).
ponytail: copied as constants for SDBT 1.00.02; read them from the .srd if a later version moves them.
"""
import hashlib
import os

from PIL import Image

SPRITES = {
    # trophy.rareType 0-4: Normal, Bronze, Silver, Gold, Platinum plates, 75px pitch.
    # 2.00 adds a sixth, rainbow plate (trophy.rareType 7).
    "CHU_UI_title_rank_00_v10.dds": {f"trophyRank_{i}": (0, 75 * i, 608, 75 * i + 72) for i in range(6)},
    # skill.category: label-less icon column of the atlas (DEFENSE/SUPPORT/BOOST/DANGER + handshake), 0 = "—".
    "CHU_UI_play_skill_00_v10.dds": {
        "skillCategory_0": (815, 421, 915, 521),
        "skillCategory_1": (504, 108, 604, 208),  # Support (heart)
        "skillCategory_2": (504, 212, 604, 312),  # Boost (explosion)
        "skillCategory_3": (504, 316, 604, 416),  # Danger (skull)
        "skillCategory_4": (504, 4, 604, 104),    # Defense (shield)
        "skillCategory_5": (504, 420, 604, 520),  # Handshake
    },
    # 1.10 moved the skill category icons here: 158px cells, 159px pitch; row 0 = unlabelled, row 2 = tier III/IV.
    "CHU_UI_Common_skill_00_v11.dds": {
        "skillCategory_0": (793, 793, 951, 951),  # none ("—"), bottom-right tile
        "skillCategory_1": (159, 0, 317, 158),    # Support
        "skillCategory_2": (0, 0, 158, 158),      # Boost1 (NORMAL I)
        "skillCategory_3": (477, 0, 635, 158),    # Danger1 (HARD I)
        "skillCategory_4": (318, 0, 476, 158),    # Defence (GUARD)
        "skillCategory_5": (636, 0, 794, 158),    # Friendship (MATCHING)
        "skillCategory_6": (795, 0, 953, 158),    # Boost2 (TARGET II)
        "skillCategory_7": (0, 318, 158, 476),    # Boost3 (TECHNICAL III)
        "skillCategory_8": (159, 318, 317, 476),  # Boost4 (MANIAC IV)
        "skillCategory_9": (318, 318, 476, 476),  # Danger2 (ABSOLUTE II)
        "skillCategory_10": (477, 318, 635, 476),  # Danger3 (CATASTROPHY III)
    },
    # 2.00 skill category gems: 3 columns x 212px pitch; the label-only (no dark tag) squares, in skill.category order.
    "CHU_UI_SkillData_00.dds": {
        f"skillCategory_{i}": (212 * c, 212 * r, 212 * c + 210, 212 * r + 210)
        for i, (c, r) in enumerate([(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (1, 0), (1, 1), (2, 3), (2, 4)])
    },
    # 1.10 ticket banners: 384x156 at 156px pitch, two columns (second starts at x=386).
    "CHU_UI_Common_ticket_00_v11.dds": {
        "ticketType_0": (0, 0, 384, 156),
        "ticketType_1": (0, 157, 384, 312),
        "ticketType_2": (0, 313, 384, 468),    # PLAYER EXP BOOST
        "ticketType_3": (0, 470, 384, 625),    # LEVEL FREE
        "ticketType_4": (0, 626, 384, 781),    # MASTER PLAY
        "ticketType_5": (0, 782, 384, 937),    # WORLD'S END PLAY
        "ticketType_6": (386, 0, 770, 156),    # BONUS TRACK PRESENT
        "ticketType_7": (386, 157, 770, 312),  # マップ進行
        "ticketType_8": (386, 313, 770, 468),  # PREMIUM TRACK
        # 1.40: type 10 (+10 squares) uses the "MAP BONUS +" banner; type 9 (statues) has none in the atlas.
        "ticketType_10": (776, 0, 1160, 156),
    },
    # ticket.type banners, 384x156 at 156px pitch in the left column. Types 2/3/6/8 have no banner in the atlas.
    "CHU_UI_Common_ticket_00.dds": {
        "ticketType_0": (0, 0, 384, 156),      # CHUNITHM-NET STANDARD
        "ticketType_1": (0, 158, 384, 312),    # CHARACTER EXP BOOST
        "ticketType_4": (0, 470, 384, 624),    # MASTER PLAY
        "ticketType_5": (0, 626, 384, 780),    # WORLD'S END PLAY
        "ticketType_7": (0, 782, 384, 936),    # マップ進行 倍
        "ticketUltima": (388, 0, 772, 156),    # ULTIMA PLAY (2.00)
        "ticketPresent_0": (893, 0, 981, 88),  # "PRESENT" corner ribbon, overlay top-right on present tickets
    },
    # 1.25 map result screen: board tile (124x59), START label, GOAL plate and MAP BONUS roundel.
    # The atlas is rewritten between versions under the same name; "file#md5prefix" keys apply only to that exact file.
    "CHU_UI_result_map_00_v11.dds": {
        "mapTile": (309, 458, 433, 517),
        "mapStart": (308, 422, 381, 450),
        "mapGoal": (458, 471, 617, 505),
        "mapBonus": (864, 422, 1054, 608),  # pink MAP BONUS roundel
    },
    # 1.40 (7e739836) and 1.50 (4ed0f0b1) moved the roundel up and reskinned the GOAL plate; rects are alpha bounding boxes.
    "CHU_UI_result_map_00_v11.dds#7e739836,4ed0f0b1": {
        "mapTile": (308, 457, 433, 518),
        "mapStart": (305, 424, 386, 448),
        "mapGoal": (465, 469, 609, 501),
        "mapBonus": (986, 245, 1178, 436),
    },
}

# 2.00 re-lays out the map result atlas (alpha bounding boxes, same elements as above).
SPRITES_2_00 = {
    "CHU_UI_result_map_00_v11.dds": {
        "mapTile": (1014, 208, 1138, 267),
        "mapStart": (219, 269, 299, 293),
        "mapGoal": (97, 62, 185, 93),
        "mapBonus": (1017, 6, 1207, 194),  # pink MAP BONUS roundel
    },
}

def export_sprites(texture_dir: str, output_dir: str, sprites: dict = SPRITES) -> list[str]:
    """Writes <name>.webp for every sprite into output_dir; returns the written filenames."""
    os.makedirs(output_dir, exist_ok=True)
    written = []
    absent = {}
    for atlas, crops in sprites.items():
        atlas, _, md5s = atlas.partition("#")
        path = os.path.join(texture_dir, atlas)
        if not os.path.exists(path):
            absent[atlas] = crops
            continue
        if md5s and not hashlib.md5(open(path, "rb").read()).hexdigest().startswith(tuple(md5s.split(","))):
            continue
        image = Image.open(path)
        for name, box in crops.items():
            image.crop(box).save(os.path.join(output_dir, f"{name}.webp"))
            written.append(f"{name}.webp")
    # atlases get renamed between versions, so only warn about sprites no present atlas supplied
    for atlas, crops in absent.items():
        if lost := [n for n in crops if f"{n}.webp" not in written]:
            print(f"Sprite atlas {atlas} not found, missing {', '.join(lost)}")
    return written

# 1.30.00 trophy.rareType -> plate: the "(楽曲名)" variants share the Gold / Platinum plate.
TROPHY_RANK_PLATE_1_30 = [0, 1, 2, 3, 3, 4, 4, 5]  # 7 (2.00): rainbow

def alias_trophy_rank_plates(sprites_dir: str) -> None:
    """Rewrites trophyRank_<rareType>.webp so index = 1.30.00 rareType (plates are cut in 0-4 order by export_sprites)."""
    plates = [Image.open(os.path.join(sprites_dir, f"trophyRank_{i}.webp")).copy() for i in range(6)]
    for rare_type, plate in enumerate(TROPHY_RANK_PLATE_1_30):
        plates[plate].save(os.path.join(sprites_dir, f"trophyRank_{rare_type}.webp"))

def alias_ticket_banners_2_00(sprites_dir: str) -> None:
    """2.00 renumbers ticket.type (0 rank boost, 1 MASTER, 2 ULTIMA, 3 WORLD'S END, 4 map progress, 5 statues, no banner)."""
    banners = {new: Image.open(os.path.join(sprites_dir, f"{old}.webp")).copy()
               for new, old in {0: "ticketType_1", 1: "ticketType_4", 2: "ticketUltima", 3: "ticketType_5", 4: "ticketType_7"}.items()}
    for name in ("ticketType_0", "ticketType_1", "ticketType_4", "ticketType_5", "ticketType_7"):
        os.remove(os.path.join(sprites_dir, f"{name}.webp"))
    for new, banner in banners.items():
        banner.save(os.path.join(sprites_dir, f"ticketType_{new}.webp"))
