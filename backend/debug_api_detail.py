import json
import requests

base = "https://webapi.sporttery.cn/gateway"

endpoints = [
    "/uniform/football/getMatchResultDetailV1.qry",
    "/uniform/football/getMatchCalculatorV1.qry",
    "/jc/football/getMatchDetailV1.qry",
    "/jc/common/getMatchDetailV1.qry",
]

params_list = [
    {"matchId": "2040613"},
    {"matchId": "2040613", "poolCode": "crs"},
    {"matchId": "2040613", "poolCode": "hhad,had"},
    {"matchIds": "2040613"},
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.sporttery.cn/",
}

for ep in endpoints:
    url = base + ep
    print(f"\n=== {ep} ===")
    for params in params_list:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            print(f"  {params}: status={resp.status_code}, len={len(resp.text)}")
            if resp.status_code == 200 and 'json' in resp.headers.get('content-type', ''):
                data = resp.json()
                print(f"    keys: {list(data.keys())}, value: {type(data.get('value'))}")
                if data.get('value'):
                    fname = f"debug_api_detail_{ep.replace('/', '_')}_{params.get('matchId', 'x')}.json"
                    with open(fname, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"    saved: {fname}")
        except Exception as e:
            print(f"  {params}: error={e}")
