"""Cut enum sprites (trophy rank plates, skill category icons) out of the surfboard UI atlases.

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
