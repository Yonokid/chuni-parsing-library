"""Enum names for the integer / ID fields in the parsed JSON.

Two sources:
  * projDB tables (App/data/db/*TableRecord.bin) back the table enums the game resolves by <str>
    (musicDif, scoreRank, notesJudgeResultID, japanRegionID, musicLableID, playOptionSpeedID, notesFieldLine).
  * Plain-int enums have no names in the data or the exe, so INT_ENUMS below is recovered from the data:
    each entry notes its evidence. Values not listed are unused in SDBT 1.00.02.
"""
import json
import os
import struct

# Record layout: u32 id, str enumName, str name, then table-specific fields; str = u32 length + UTF-8.
# ponytail: per-table extra fields are unknown, so records are located by scanning for the next
# sequential id + two valid strings. Decodes every table in SDBT 1.00.02; give tables real layouts if one breaks.
def _read_str(b: bytes, o: int) -> tuple[str, int]:
    n = struct.unpack_from("<I", b, o)[0]
    if n > 512 or o + 4 + n > len(b):
        raise ValueError
    return b[o + 4:o + 4 + n].decode("utf-8"), o + 4 + n

def _record_at(b: bytes, o: int, want_id: int):
    try:
        if struct.unpack_from("<I", b, o)[0] != want_id:
            return None
        enum_name, p = _read_str(b, o + 4)
        name, p = _read_str(b, p)
    except (ValueError, struct.error, UnicodeDecodeError):
        return None
    return (enum_name, name, p) if enum_name.isprintable() and enum_name else None

def read_table(path: str) -> list[dict]:
    b = open(path, "rb").read()
    records, o = [], 4
    for i in range(struct.unpack_from("<I", b, 0)[0]):
        hit = _record_at(b, o, i)
        while hit is None:
            o += 1
            if o > len(b) - 12:
                raise ValueError(f"{os.path.basename(path)}: record {i} not found")
            hit = _record_at(b, o, i)
        enum_name, name, o = hit
        records.append({"id": i, "enumName": enum_name, "name": name})
    return records

# JSON field -> projDB table. Parsed JSON carries the enumName (e.g. musicLabel "ID_000"); look up "name" here.
DB_TABLES = {
    "musicDifficulty": "MusicDif",
    "scoreRank": "ScoreRank",
    "notesJudgeResult": "NotesJudgeResult",
    "japanRegion": "JapanRegion",
    "musicLabel": "MusicLabel",
    "playOptionSpeed": "PlayOptionSpeed",
    "notesFieldLine": "FieldLineFile",
    "notesTypes": "NotesSkillType",
}

INT_ENUMS = {
    # ConditionSubData.type: selects the active sub-struct; matches the deserializer's field order and the data.
    "condition.type": {0: "event", 1: "playMusic", 2: "playSetting", 3: "playMusicResult", 4: "playTotalResult",
                       5: "person", 6: "chara", 7: "skill", 8: "trophy", 9: "travel", 10: "music"},
    # SkillSubstanceData.type: 0/1/2/3/5 confirmed by the SkillPlaying setup switch (0xe256c0); 4/6/7 from the data. See skill.SUBSTANCES.
    "skill.substance.type": {0: "gaugeAssist", 1: "gaugeKeep", 2: "damageGuard", 3: "deathPenalty",
                             4: "changeJudgeIni", 5: "changeJudgeResult", 6: "changeSpeed", 7: "changeImg"},
    # EventData.substances.type: see event.SUBSTANCES.
    # 10: in 2.05 the one type-10 event fills avatarAccessoryGacha (kind "avatarAccessoryGacha"), not changeSurfBoardUI.
    "event.substance.type": {0: "flag", 1: "information", 2: "map", 3: "music", 4: "advertiseMovie", 5: "recommendMusic", 6: "release", 7: "course", 8: "quest", 9: "duel", 10: "changeSurfBoardUI", 11: "rightsInfo", 12: "battleReward", 13: "dailyBonusPreset", 14: "cmission", 16: "unlockChallenge", 17: "linkedVerse"},
    # Skill explain texts: award 1/2/3 skills say FULL COMBO / FULL CHAIN / ALL JUSTICE (not the ScoreAward table order).
    "skill.timing.award": {0: "None", 1: "FULL COMBO", 2: "FULL CHAIN", 3: "ALL JUSTICE"},
    # Skill explain texts: scene 1 "ゲーム開始時", 2 "ゲーム終了時"; the only scene-3 skill (乙女街道) does both.
    # Code (0xe23420): 2 banks the bonus for game end; 1 and 3 are skipped by the in-play trigger.
    "skill.timing.scene": {0: "During play", 1: "Game start", 2: "Game end", 3: "Game start and end"},
    # Judge compared with notesJudgeResult (Guilty 0 < Attack 1 < Justice 2 < JusticeCritical 3); confirmed by the
    # comparators the trigger calls: 1 -> judge >= id (0xe16a60), 2 -> == (0xd83a50), 3 -> <= (0xd6ace0), 0 -> any.
    "skill.timing.notesJudgeResultRange": {0: "Any", 1: "Or better", 2: "Exactly", 3: "Or worse"},
    # Use counter (0xe25e90): 2 counts remaining uses down (useLimit true for all 53 such skills), 1 counts up to a cap.
    "skill.counterType": {0: "None", 1: "Count up", 2: "Use count"},
    # CharaRankData.type: 1 rows carry a skill, 2 rows a flavor text file.
    "chara.rank.type": {1: "Skill", 2: "Flavor text"},
    # MapAreaGridData.type (== displayType): 1 is always the first grid, 2 the last, 3 the reward grids between.
    "mapArea.grid.type": {1: "Start", 2: "Goal", 3: "Normal"},
    # Named by the items that use them. Banners (sprites ticketType_N) exist for 0/1/4/5/7 only.
    "ticket.type": {0: "CHUNITHM-NET access", 1: "Character rank boost", 2: "Player Lv boost",
                    3: "Challenge song all-difficulty play", 4: "MASTER play", 5: "WORLD'S END play", 6: "Extra track",
                    7: "Map progress boost", 8: "Premium", 9: "Character rank limit unlock",
                    10: "Map fixed squares boost"},  # "+10 squares for 3 songs"
    # RewardSubsubstance.type: which of gamePoint/ticket/trophy/chara/skill/namePlate is set (music, 6, is unused).
    # 7/8 (1.40): mapIcon/systemVoice set, seen in the duel rewards.
    "reward.type": {0: "Game points", 1: "Ticket", 2: "Trophy", 3: "Character", 4: "Skill", 5: "Name plate", 6: "Music", 7: "Map icon", 8: "System voice"},
    "map.mapType": {0: "Normal", 1: "Endless", 2: "Event", 3: "Episode"},  # 3 (1.40): "AMAZON ep. I-VII/EX" maps
    "gameTable.tableType": {0: "Player level", 1: "Player EXP bonus", 2: "Character rank", 3: "NG words",
                            4: "Name entry A-Z", 5: "Name entry a-z", 6: "Name entry numbers", 7: "Name entry marks",
                            8: "External characters", 9: "Advertise update date"},
    "rightsInfo.type": {0: "Copyright", 1: "Advertise"},
    "skill.rareType": {0: "Normal", 1: "Rare"},
    # surfboard/texture: CHU_UI_title_rank_00_v10.dds plates (grey, copper, silver, gold, platinum) and the
    # CHU_UI_Userbox_00_v10.dds legend ノーマル/ブロンズ/シルバー/ゴールド/プラチナ称号, in rareType order 0-4.
    "trophy.rareType": {0: "Normal", 1: "Bronze", 2: "Silver", 3: "Gold", 4: "Platinum"},
    # CHU_UI_play_skill_00_v10.dds labels DEFENSE/SUPPORT/BOOST/DANGER SKILL + an unlabelled handshake icon;
    # matched by content: 1 = heal skills, 2 = gauge boosts, 3 = deathPenalty/strict-judge risks,
    # 4 = guards, 5 = chain skills (handshake). 0 is only used by スキルなし.
    "skill.category": {0: "None", 1: "Support", 2: "Boost", 3: "Danger", 4: "Defense", 5: "Handshake (unlabelled)",
                       # 1.10 splits the game's own categories (Boost1-4, Danger1-3)
                       6: "Boost 2", 7: "Boost 3", 8: "Boost 4", 9: "Danger 2", 10: "Danger 3"},
}

# 1.30.00 adds separate "(楽曲名)" plates: CHU_UI_Userbox_00_v11.dds legend ノーマル/ブロンズ/シルバー/ゴールド/ゴールド(楽曲名)/プラチナ/プラチナ(楽曲名).
TROPHY_RARE_TYPE_1_30 = {0: "Normal", 1: "Bronze", 2: "Silver", 3: "Gold", 4: "Gold (song name)", 5: "Platinum", 6: "Platinum (song name)", 7: "Rainbow",  # 7: 2.00 (CHU_UI_title_rank_00_v10 sixth plate)
                           8: "ULTIMA ALL JUSTICE",  # 8 (2.45): song trophies "<song>/ULTIMA/ALL JUSTICE達成"
                           # 18-22 (2.30) named from their trophies; 9-11, 13-17 are unnamed (no plate art cut for them)
                           18: "Spirit", 19: "Tribute", 20: "Legend", 21: "KOP Finalist", 22: "KOP Champion"}

# 2.00.00 (NEW!!) renumbers several enums: skills become seeds, MASTER/ULTIMA/WORLD'S END are separate tickets.
INT_ENUMS_2_00 = {
    "ticket.type": {0: "Character rank boost", 1: "MASTER play", 2: "ULTIMA play", 3: "WORLD'S END play",
                    4: "Map progress boost", 5: "Character rank limit unlock",  # 5: statues, no banner
                    7: "EXP stock", 8: "All-difficulty play"},  # 8 (2.50): MASTER/ULTIMA/WORLD'S END play at once  # 2.10: recycleCharaExp; 6 (playMusicPlus) unused
    # 9 avatarAccessory, 12 ultimaScore (2.20); 10/11 (frame/symbolChat?) are unused in shipped data
    "reward.type": {**INT_ENUMS["reward.type"], 4: "Skill seed", 9: "Avatar item", 12: "ULTIMA score",
                    13: "Stage", 14: "Mate"},  # 13: 2.40, 14: 2.50
    "chara.rank.type": {1: "Skill seed", 2: "Flavor text"},
    # Gem icons of CHU_UI_SkillData_00.dds, named by the skills that use each category.
    "skill.category": {0: "None", 1: "Guard", 2: "Support", 3: "Boost", 4: "Combo", 5: "A-Break", 6: "Judge", 7: "Judge+",
                       8: "Absolute", 9: "Absolute+", 10: "Catastrophy", 11: "Unlimited", 12: "Unlimited+",
                       # 2.05: one skill each (絆・限界突破の証, キャンペーンブースト); icons UNLIMITED++ and CAMPAIGN
                       13: "Unlimited++", 14: "Campaign",
                       16: "Brave"},  # 16 (2.40): 勇気のしるし [BRAVE]
    # AvatarAccessory.category: DMY_Avatar* textures are Wear/Head/Face/Skin/Item/Front/Back; 4 vs 6 and 7 are unconfirmed
    # (1/2/3/5 match the item names, 6 is the only layerIndex 1).
    "avatarAccessory.category": {1: "Wear", 2: "Head", 3: "Face", 4: "Skin", 5: "Item", 6: "Front", 7: "Back"},
    "teamPresent.category": {1: "Individual", 2: "Team"},
}

def is_2_00(output_dir: str | None) -> bool:
    """True for output whose skills are seeds (2.00.00+): ticket/reward/skill enums were renumbered."""
    path = os.path.join(output_dir or "", "skill", "skill.json")
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        return any("seedName" in s for s in json.load(f))

def has_song_name_rarity(output_dir: str | None) -> bool:
    """True for versions whose trophy.rareType uses TROPHY_RARE_TYPE_1_30 (ids were reordered in 1.30.00)."""
    path = os.path.join(output_dir or "", "trophy", "trophy.json")
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        return any(t["rareType"] > 4 for t in json.load(f))

def build_enums(db_dir: str, output_dir: str | None = None) -> dict:
    tables = {
        field: read_table(os.path.join(db_dir, f"{table}TableRecord.bin"))
        for field, table in DB_TABLES.items()
        if os.path.exists(os.path.join(db_dir, f"{table}TableRecord.bin"))
    }
    ints = INT_ENUMS
    if has_song_name_rarity(output_dir):
        ints = {**INT_ENUMS, "trophy.rareType": TROPHY_RARE_TYPE_1_30}
    if is_2_00(output_dir):
        ints = {**ints, **INT_ENUMS_2_00}
    return {"tables": tables, "ints": ints}

if __name__ == "__main__":
    import sys
    db = build_enums(sys.argv[1])["tables"]
    assert [r["name"] for r in db["musicDifficulty"]] == ["BASIC", "ADVANCED", "EXPERT", "MASTER", "WORLD`S END"]
    assert db["notesJudgeResult"][3]["enumName"] == "JusticeCritical"
    for field, records in db.items():
        print(field, [(r["enumName"], r["name"]) for r in records][:6])
