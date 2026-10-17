"""Cut enum sprites (trophy rank plates, skill category icons, ticket banners) out of the surfboard UI atlases.

Rects are (left, top, right, bottom) pixels from the CROP chunks of the matching .srd layouts
(common/trophyRank/CHU_UI_Character_title_rank_00_v10.srd, common/skillInfo/CHU_UI_SkillData_00_v10.srd).
ponytail: copied as constants for SDBT 1.00.02; read them from the .srd if a later version moves them.
"""
import os

from PIL import Image

SPRITES = {
    # trophy.rareType 0-4: Normal, Bronze, Silver, Gold, Platinum plates, 75px pitch.
    "CHU_UI_title_rank_00_v10.dds": {f"trophyRank_{i}": (0, 75 * i, 608, 75 * i + 72) for i in range(5)},
    # skill.category: label-less icon column of the atlas (DEFENSE/SUPPORT/BOOST/DANGER + handshake), 0 = "—".
    "CHU_UI_play_skill_00_v10.dds": {
        "skillCategory_0": (815, 421, 915, 521),
        "skillCategory_1": (504, 108, 604, 208),  # Support (heart)
        "skillCategory_2": (504, 212, 604, 312),  # Boost (explosion)
        "skillCategory_3": (504, 316, 604, 416),  # Danger (skull)
        "skillCategory_4": (504, 4, 604, 104),    # Defense (shield)
        "skillCategory_5": (504, 420, 604, 520),  # Handshake
    },
    # ticket.type banners, 384x156 at 156px pitch in the left column. Types 2/3/6/8 have no banner in the atlas.
    "CHU_UI_Common_ticket_00.dds": {
        "ticketType_0": (0, 0, 384, 156),      # CHUNITHM-NET STANDARD
        "ticketType_1": (0, 158, 384, 312),    # CHARACTER EXP BOOST
        "ticketType_4": (0, 470, 384, 624),    # MASTER PLAY
        "ticketType_5": (0, 626, 384, 780),    # WORLD'S END PLAY
        "ticketType_7": (0, 782, 384, 936),    # マップ進行 倍
        "ticketPresent_0": (893, 0, 981, 88),  # "PRESENT" corner ribbon, overlay top-right on present tickets
    },
}

def export_sprites(texture_dir: str, output_dir: str) -> list[str]:
    """Writes <name>.webp for every sprite into output_dir; returns the written filenames."""
    os.makedirs(output_dir, exist_ok=True)
    written = []
    for atlas, crops in SPRITES.items():
        path = os.path.join(texture_dir, atlas)
        if not os.path.exists(path):
            print(f"Sprite atlas {atlas} not found, skipping")
            continue
        image = Image.open(path)
        for name, box in crops.items():
            image.crop(box).save(os.path.join(output_dir, f"{name}.webp"))
            written.append(f"{name}.webp")
    return written
