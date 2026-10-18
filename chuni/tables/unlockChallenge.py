import xml.etree.ElementTree as ET

from chuni.utils import get_bool, get_int, get_ref, get_text_element, get_version, safe_find


def parse_unlockChallenge(file: str) -> dict:
    with open(file, "r", encoding="utf-8") as xml_file:
        json_data = dict()

        tree = ET.parse(xml_file)
        root = tree.getroot()

        json_data["id"] = int(get_text_element(root, "name/id"))
        json_data["version"] = get_version(root)
        json_data["name"] = get_text_element(root, "name/str")
        json_data["disableFlag"] = get_bool(root, "disableFlag")
        # each list entry is a wrapper <type> + one data struct (type is always 0)
        musics = []
        for sub in safe_find(root, "musicList/list"):
            music = safe_find(sub, "unlockChallengeMusicData")
            musics.append({
                "music": get_ref(music, "name"),
                "rewards": [{"reward": get_ref(r, "rewardName"), "num": get_int(r, "rewardNum")}
                            for r in (s.find("unlockChallengeRewardData") for s in safe_find(music, "rewardList/list"))],
                "courses": [get_ref(c, "courseName")
                            for c in (s.find("unlockChallengeCourseData") for s in safe_find(music, "courseList/list"))],
            })
        json_data["musics"] = musics

    return json_data
