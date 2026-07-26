import json
import urllib.request
import urllib.error
import urllib.parse

BASE_URL = "http://localhost:8000"

# 用户提供的千问预测数据（markdown 表格转义后）
RAW_DATA = """
| 编号 | 赛事 | 对阵 | 推荐比分 | 推荐半全场 |
| :--- | :--- | :--- | :--- | :--- |
| 周六201 | 韩职 | 金泉尚武 VS 大田市民 | 2-1 / 1-1 | 平胜 / 平平 |
| 周六202 | 韩职 | 浦项制铁 VS 全北现代 | 1-1 / 1-2 | 平负 / 负负 |
| 周六203 | 瑞超 | 代格福什 VS 佐加顿斯 | 0-2 / 1-2 | 负负 |
| 周六204 | 芬超 | 玛丽港 VS AC奥卢 | 1-0 / 2-1 | 平胜 / 胜胜 |
| 周六205 | 挪超 | 克里斯蒂 VS 斯达 | 2-1 / 3-1 | 胜胜 |
| 周六206 | 芬超 | 库奥皮奥 VS 瓦萨 | 2-0 / 3-0 | 胜胜 |
| 周六207 | 瑞超 | 卡尔马 VS 米亚尔比 | 1-1 / 0-1 | 平负 / 负负 |
| 周六208 | 巴甲 | 巴竞技 VS 巴西国际 | 1-0 / 1-1 | 平胜 / 平平 |
| 周六209 | 巴甲 | 桑托斯 VS 沙佩科 | 2-0 / 2-1 | 胜胜 / 平胜 |
| 周六210 | 美职 | 圣迭戈FC VS 达拉斯 | 1-1 / 2-1 | 平平 / 平胜 |
| 周六211 | 美职 | 圣何塞 VS 洛城银河 | 1-2 / 2-2 | 负负 / 平负 |
| 周日201 | 韩职 | 首尔FC VS 蔚山现代 | 2-1 / 1-0 | 胜胜 / 平胜 |
| 周日202 | 韩职 | 仁川联 VS 富川FC | 1-0 / 2-0 | 平胜 / 胜胜 |
| 周日203 | 韩职 | 光州FC VS 济州SK | 1-1 / 2-1 | 平平 / 平胜 |
| 周日204 | 韩职 | 安养FC VS 江原FC | 0-1 / 1-2 | 负负 / 平负 |
| 周日205 | 瑞超 | 布鲁马波 VS 哈马比 | 1-2 / 1-3 | 负负 / 平负 |
| 周日206 | 瑞超 | 天狼星 VS 哥德堡 | 2-1 / 2-2 | 胜胜 / 平胜 |
| 周日207 | 芬超 | 国际图尔 VS 赫尔火花 | 1-0 / 1-1 | 平胜 / 平平 |
| 周日208 | 芬超 | 坦山猫 VS 拉赫蒂 | 2-0 / 3-1 | 胜胜 |
| 周日209 | 挪超 | 布兰 VS 瓦勒伦加 | 2-1 / 3-1 | 胜胜 / 平胜 |
| 周日210 | 芬超 | 赫尔辛基 VS TPS图尔 | 1-0 / 2-0 | 平胜 / 胜胜 |
| 周日211 | 瑞超 | 盖斯 VS 哈尔姆斯 | 1-1 / 0-0 | 平平 |
"""


def normalize_half_full(hf: str) -> str:
    """把 '平胜' 转成 '平/胜'"""
    hf = hf.strip()
    if "/" in hf:
        return hf
    # 两个汉字，如 平胜、负负、胜胜
    if len(hf) == 2:
        return f"{hf[0]}/{hf[1]}"
    return hf


def parse_scores(score_str: str):
    """解析 '2-1 / 1-1' -> [(2,1), (1,1)]"""
    parts = [p.strip() for p in score_str.split("/")]
    result = []
    for part in parts:
        home, away = part.split("-")
        result.append((int(home.strip()), int(away.strip())))
    return result


def parse_half_fulls(hf_str: str):
    """解析 '平胜 / 平平' -> ['平/胜', '平/平']"""
    parts = [normalize_half_full(p) for p in hf_str.split("/")]
    return parts


def parse_table(raw: str):
    rows = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 5 or cells[0] in ("编号", "") or cells[0].startswith(":-"):
            continue
        match_id = cells[0]
        scores = parse_scores(cells[3])
        half_fulls = parse_half_fulls(cells[4])
        # 如果半全场只有一个，复制成两个相同
        if len(half_fulls) == 1 and len(scores) == 2:
            half_fulls = [half_fulls[0], half_fulls[0]]
        rows.append({
            "match_id": match_id,
            "scores": scores,
            "half_fulls": half_fulls,
        })
    return rows


def import_match(row: dict):
    match_id = row["match_id"]
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

    # 取第一条预测的半全场作为整体半全场（后端每条预测会复用）
    payload = {
        "provider_name": "qianwen",
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
    rows = parse_table(RAW_DATA)
    imported = 0
    failed = []
    for row in rows:
        result = import_match(row)
        if "error" in result:
            failed.append((row["match_id"], result))
        else:
            imported += 1
            print(f"✅ {row['match_id']}: {result}")

    print(f"\n导入完成：成功 {imported} 场，失败 {len(failed)} 场")
    if failed:
        for mid, err in failed:
            print(f"❌ {mid}: {err}")
