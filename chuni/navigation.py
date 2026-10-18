"""navigation.json: the viewer's sidebar entries for one version, limited to the data types that version has."""
import json
import os

SEGMENTS = [
    ("music", "Music", "AlbumIcon"),
    ("chara", "Characters", "Person2Icon"),
    ("skill", "Skills", "AutoAwesomeIcon"),
    ("trophy", "Trophies", "EmojiEventsIcon"),
    ("event", "Events", "EventIcon"),
    ("map", "Maps", "MapIcon"),
    ("movie", "Movies", "MovieIcon"),
    ("present", "Presents", "CardGiftcardIcon"),
    ("shop", "Shop", "ShoppingCartIcon"),
    ("stage", "Stages", "ViewCarouselIcon"),
    ("ticket", "Tickets", "LocalActivityIcon"),
    ("reward", "Rewards", "RedeemIcon"),
    ("course", "Courses", "FlagIcon"),
    ("namePlate", "Name Plates", "BadgeIcon"),
    ("quest", "Quests", "ExploreIcon"),
    ("chargeItem", "Charge Items", "PaymentsIcon"),
    ("duel", "Duels", "SportsMmaIcon"),
    ("systemVoice", "System Voices", "RecordVoiceOverIcon"),
    ("mapIcon", "Map Icons", "PinDropIcon"),
    ("avatarAccessory", "Avatar Items", "FaceIcon"),
    ("avatarAccessoryGacha", "Avatar Gacha", "CasinoIcon"),
    ("frame", "Frames", "FilterFramesIcon"),
    ("symbolChat", "Symbol Chat", "ChatIcon"),
    ("gacha", "Gacha", "StyleIcon"),
    ("battleReward", "Battle Rewards", "MilitaryTechIcon"),
    ("teamPresent", "Team Presents", "GroupsIcon"),
    ("teamPresentPreset", "Team Present Sets", "PlaylistAddCheckIcon"),
]

def write_navigation(output_dir: str) -> None:
    entries = [{"segment": s, "title": t, "icon": i} for s, t, i in SEGMENTS
               if os.path.exists(os.path.join(output_dir, s, f"{s}.json"))]
    with open(os.path.join(output_dir, "navigation.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
