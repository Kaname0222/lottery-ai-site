import json
import requests
from datetime import datetime

base = "https://webapi.sporttery.cn/gateway"

endpoints = [
    "/uniform/football/getMatchCalculatorV1.qry",
    "/jc/common/getSupportRateV1.qry",
    "/jc/football/getMatchResultV1.qry",
    "/uniform/football/getMatchResultDetailV1.qry",
    "/uniform/football/getUniformMatchResultV1.qry",
]

params_variants = [
    {"businessDate": "2026-07-25", "channel": "c", "poolCode": "crs"},
    {"saleDate": "2026-07-25", "channel": "c", "poolCode": "crs"},
    {"matchDate": "2026-07-25", "channel": "c", "poolCode": "crs"},
    {"matchId": "2040613", "poolCode": "crs"},
    {"matchIds": "2040613", "poolCode": "crs"},
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.lottery.gov.cn/",
}

for ep in endpoints:
    url = base + ep
    print(f"\n=== Endpoint: {ep} ===")
    for params in params_variants[:2]:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            print(f"  {params}: status={resp.status_code}, content-type={resp.headers.get('content-type')}, len={len(resp.text)}")
            if resp.status_code == 200 and 'json' in resp.headers.get('content-type', ''):
                data = resp.json()
                print(f"    keys: {list(data.keys())}, value type: {type(data.get('value'))}")
        except Exception as e:
            print(f"  {params}: error={e}")
