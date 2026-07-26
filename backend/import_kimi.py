import json
import urllib.request
import urllib.error
import urllib.parse
import re

BASE_URL = "http://localhost:8000"

# 用户提供的 Kimi 预测数据
RAW_DATA = """
|    编号   | 对阵          | 联赛 | 比分预测    | 半全场预测 | 
 | :-----: | :---------- | :- | :------ | :---- | 
 | **201** | 赫根 VS 索尔纳   | 瑞超 | 1-1、2-1 | 平平、平胜 | 
 | **202** | 罗森博格 VS 腓特烈 | 挪超 | 2-1、1-1 | 平胜、平平 | 
 |    编号   | 对阵            | 联赛 | 比分预测    | 半全场预测  | 
 | :-----: | :------------ | :- | :------ | :----- | 
 | **201** | 首尔FC VS 蔚山现代  | 韩职 | 1-2、1-1 | 平负、平平  | 
 | **202** | 仁川联 VS 富川FC   | 韩职 | 1-0、2-1 | 平胜、胜胜  | 
 | **203** | 光州FC VS 济州SK  | 韩职 | 1-1、2-1 | 平平、平胜  | 
 | **204** | 安养FC VS 江原FC  | 韩职 | 1-1、1-2 | 平平、平负  | 
 | **205** | 布鲁马波 VS 哈马比   | 瑞超 | 1-2、0-2 | 平负、负负  | 
 | **206** | 天狼星 VS 哥德堡    | 瑞超 | 1-1、1-2 | 平平、平负  | 
 | **207** | 国际图尔 VS 赫尔火花  | 芬超 | 2-1、1-1 | 平胜、平平  | 
 | **208** | 坦山猫 VS 拉赫蒂    | 芬超 | 2-1、1-1 | 平胜、平平  | 
 | **209** | 布兰 VS 瓦勒伦加    | 挪超 | 2-1、2-2 | 平胜、胜胜  | 
 | **210** | 赫尔辛基 VS TPS图尔 | 芬超 | **2-0** | **胜胜** | 
 | **211** | 盖斯 VS 哈尔姆斯    | 瑞超 | 1-1、2-1 | 平平、平胜  | 
 | **212** | 马尔默 VS 埃夫斯堡   | 瑞超 | 2-1、1-1 | 平胜、平平  | 
 | **213** | 萨普斯堡 VS 汉坎    | 挪超 | 2-1、1-1 | 平胜、平平  | 
 | **214** | 奥斯KFUM VS 莫尔德 | 挪超 | 1-2、0-2 | 平负、负负  | 
 | **215** | 桑纳菲 VS 博德闪耀   | 挪超 | **1-3** | **负负** | 
 | **216** | 奥勒松 VS 维京     | 挪超 | 1-2、1-1 | 平负、平平  | 
 | **217** | 弗拉门戈 VS 圣保罗   | 巴甲 | 1-0、2-1 | 平胜、胜胜  | 
 | **218** | 格雷米奥 VS 弗鲁米嫩  | 巴甲 | 1-1、2-1 | 平平、平胜  | 
 |    编号   | 对阵           | 联赛 | 比分预测    | 半全场预测  | 
 | :-----: | :----------- | :- | :------ | :----- | 
 | **201** | 金泉尚武 VS 大田市民 | 韩职 | 1-1、2-1 | 平平、平胜  | 
 | **202** | 浦项制铁 VS 全北现代 | 韩职 | 2-1、1-1 | 平胜、平平  | 
 | **203** | 代格福什 VS 佐加顿斯 | 瑞超 | 0-2、1-2 | 负负、平负  | 
 | **204** | 玛丽港 VS AC奥卢  | 芬超 | 1-1、2-1 | 平平、平胜  | 
 | **205** | 克里斯蒂 VS 斯达   | 挪超 | 2-1、1-1 | 平胜、平平  | 
 | **206** | 库奥皮奥 VS 瓦萨   | 芬超 | **2-0** | **胜胜** | 
 | **207** | 卡尔马 VS 米亚尔比  | 瑞超 | 1-1、1-2 | 平平、平负  | 
 | **208** | 巴竞技 VS 巴西国际  | 巴甲 | 1-1、1-0 | 平平、平胜  | 
 | **209** | 桑托斯 VS 沙佩科   | 巴甲 | **2-0** | **胜胜** | 
 | **210** | 圣迭戈FC VS 达拉斯 | 美职 | 2-1、1-1 | 平胜、平平  | 
 | **211** | 圣何塞 VS 洛城银河  | 美职 | 1-2、1-1 | 平负、平平  |
"""


def normalize_half_full(hf: str) -> str:
    """把 '平胜' 转成 '平/胜'"""
    hf = hf.strip()
    if "/" in hf:
        return hf
    if len(hf) == 2:
        return f"{hf[0]}/{hf[1]}"
    return hf


def parse_scores(score_str: str):
    """解析 '1-1、2-1' 或 '**2-0**' -> [(1,1), (2,1)]"""
    score_str = score_str.replace("**", "").strip()
    # 支持中文顿号或英文逗号分隔
    parts = [p.strip() for p in re.split(r"[、,]", score_str) if p.strip()]
    result = []
    for part in parts:
        home, away = part.split("-")
        result.append((int(home.strip()), int(away.strip())))
    return result


def parse_half_fulls(hf_str: str):
    """解析 '平平、平胜' 或 '**胜胜**' -> ['平/平', '平/胜']"""
    hf_str = hf_str.replace("**", "").strip()
    parts = [normalize_half_full(p) for p in re.split(r"[、,]", hf_str) if p.strip()]
    return parts


def parse_teams(matchup: str):
    """解析 '赫根 VS 索尔纳' -> ('赫根', '索尔纳')"""
    parts = [p.strip() for p in re.split(r"\s+VS\s+", matchup, flags=re.IGNORECASE)]
    if len(parts) != 2:
        return None, None
    return parts[0], parts[1]


def parse_table(raw: str):
    rows = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 5 or cells[0] in ("编号", "") or cells[0].startswith(":-"):
            continue
        home, away = parse_teams(cells[1])
        if not home:
            continue
        scores = parse_scores(cells[3])
        half_fulls = parse_half_fulls(cells[4])
        # 如果只有一个比分，复制成两个相同
        if len(scores) == 1:
            scores = [scores[0], scores[0]]
        # 如果只有一个半全场，复制成两个相同
        if len(half_fulls) == 1:
            half_fulls = [half_fulls[0], half_fulls[0]]
        rows.append({
            "home": home,
            "away": away,
            "league": cells[2],
            "scores": scores,
            "half_fulls": half_fulls,
        })
    return rows


def fetch_all_matches():
    url = f"{BASE_URL}/matches"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def find_match_id(matches, home: str, away: str):
    """根据主客队名模糊匹配比赛"""
    for m in matches:
        db_home = m["home_team"]
        db_away = m["away_team"]
        # 直接包含关系（允许简写）
        if (home in db_home or db_home in home) and (away in db_away or db_away in away):
            return m["match_id"]
    return None


def import_match(match_id: str, row: dict):
    scores = row["scores"]
    half_fulls = row["half_fulls"]

    predictions = []
    for idx, ((home, away), hf) in enumerate(zip(scores, half_fulls), start=1):
        predictions.append({
            "prediction_index": idx,
            "home_score": home,
            "away_score": away,
            "confidence": None,
            "reasoning_summary": None,
            "market_reasoning": None,
            "bets": None,
            "is_correct": None,
            "points_awarded": None,
            "direction_points": None,
            "other_points": None,
        })

    payload = {
        "provider_name": "kimi",
        "half_full": half_fulls[0] if half_fulls else None,
        "predictions": predictions,
    }

    url = f"{BASE_URL}/matches/{urllib.parse.quote(match_id)}/manual-prediction"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}


if __name__ == "__main__":
    matches = fetch_all_matches()
    rows = parse_table(RAW_DATA)

    imported = 0
    failed = []
    skipped_no_match = []

    for row in rows:
        match_id = find_match_id(matches, row["home"], row["away"])
        if not match_id:
            skipped_no_match.append(f"{row['home']} VS {row['away']}")
            continue
        result = import_match(match_id, row)
        if "error" in result:
            failed.append((match_id, result))
        else:
            imported += 1
            print(f"✅ {match_id} ({row['home']} VS {row['away']}): {result}")

    print(f"\n导入完成：成功 {imported} 场，失败 {len(failed)} 场，未找到比赛 {len(skipped_no_match)} 场")
    if failed:
        for mid, err in failed:
            print(f"❌ {mid}: {err}")
    if skipped_no_match:
        print("未找到对应比赛：")
        for s in skipped_no_match:
            print(f"  - {s}")
