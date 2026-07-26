import json
import requests
from datetime import datetime, timedelta

url = "https://webapi.sporttery.cn/gateway/uniform/football/getUniformMatchResultV1.qry"

end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

params_list = [
    {"startDate": start_date, "endDate": end_date, "matchId": "", "pageNo": 1, "pageSize": 100, "timestamp": int(datetime.now().timestamp() * 1000)},
    {"startDate": "2026-07-25", "endDate": "2026-07-25", "matchId": "", "pageNo": 1, "pageSize": 100, "timestamp": int(datetime.now().timestamp() * 1000)},
    {"matchId": "2040613", "pageNo": 1, "pageSize": 10, "timestamp": int(datetime.now().timestamp() * 1000)},
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.lottery.gov.cn/",
}

for params in params_list:
    print(f"\n=== Params: {params} ===")
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"Status: {resp.status_code}")
        print(f"URL: {resp.url}")
        data = resp.json()
        print(f"Keys: {list(data.keys())}")
        if "value" in data:
            value = data["value"]
            print(f"value type: {type(value)}")
            if isinstance(value, dict):
                print(f"value keys: {list(value.keys())[:20]}")
                if "matchResult" in value:
                    print(f"matchResult count: {len(value['matchResult'])}")
                    for m in value["matchResult"][:3]:
                        print(f"  {m.get('matchNumStr')} {m.get('matchId')}: {m.get('homeTeam')} VS {m.get('awayTeam')}")
                        print(f"    keys: {list(m.keys())[:30]}")
            elif isinstance(value, list):
                print(f"value list count: {len(value)}")
        fname = f"debug_api_result_{params.get('startDate', params.get('matchId', 'default'))}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {fname}")
    except Exception as e:
        print(f"Error: {e}")
