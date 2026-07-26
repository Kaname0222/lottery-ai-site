import json
import requests

url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry"

# 测试不同参数
params_list = [
    {"channel": "c", "poolCode": "crs"},
    {"channel": "c", "poolCode": "crs", "matchId": "2040613"},
    {"channel": "c", "poolCode": "crs", "matchIds": "2040613"},
    {"channel": "c", "poolCode": "crs", "date": "2026-07-25"},
    {"channel": "c", "poolCode": "crs", "matchDate": "2026-07-25"},
    {"channel": "c", "poolCode": "crs", "saleDate": "2026-07-25"},
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
        try:
            data = resp.json()
            print(f"Keys: {list(data.keys())[:10]}")
            if "value" in data:
                value = data["value"]
                print(f"value type: {type(value)}")
                if isinstance(value, dict):
                    print(f"value keys: {list(value.keys())[:10]}")
                    if "matchResultList" in value:
                        print(f"matchResultList count: {len(value['matchResultList'])}")
                        for m in value["matchResultList"][:3]:
                            print(f"  {m.get('matchId')} {m.get('homeTeam', {}).get('name')} VS {m.get('awayTeam', {}).get('name')}")
                elif isinstance(value, list):
                    print(f"value list count: {len(value)}")
                    for m in value[:3]:
                        print(f"  {m.get('matchId')} {m.get('homeTeam', {}).get('name')} VS {m.get('awayTeam', {}).get('name')}")
            # 保存完整响应
            fname = f"debug_api_crs_{params.get('matchId', params.get('date', params.get('matchDate', 'default')))}.json"
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved to {fname}")
        except Exception as e:
            print(f"Parse error: {e}")
            print(f"Text preview: {resp.text[:500]}")
    except Exception as e:
        print(f"Request error: {e}")
