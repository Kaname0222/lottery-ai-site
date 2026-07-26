import json
import requests

url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry"

params = {
    "channel": "c",
    "poolCode": "crs",
    "saleDate": "2026-07-25",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.lottery.gov.cn/",
}

resp = requests.get(url, params=params, headers=headers, timeout=30)
print(f"Status: {resp.status_code}")
print(f"URL: {resp.url}")
data = resp.json()

with open("debug_api_crs_saledate_20260725.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("Saved to debug_api_crs_saledate_20260725.json")

value = data.get("value", {})
print(f"\nvalue keys: {list(value.keys())}")
print(f"totalCount: {value.get('totalCount')}")
print(f"matchDateList: {value.get('matchDateList')}")

for mi in value.get("matchInfoList", []):
    print(f"\nbusinessDate: {mi.get('businessDate')}, subMatchList count: {len(mi.get('subMatchList', []))}")
    for m in mi.get("subMatchList", [])[:10]:
        print(f"  {m.get('matchNum')} {m.get('matchId')}: {m.get('homeTeamAbbName')} VS {m.get('awayTeamAbbName')}")
