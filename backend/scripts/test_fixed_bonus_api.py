import requests

mid = '2040632'
url = 'https://webapi.sporttery.cn/gateway/uniform/football/getFixedBonusV1.qry'
params = {
    'clientCode': '1',
    'sportteryMatchId': mid,
}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.sporttery.cn/',
    'Origin': 'https://www.sporttery.cn',
}
resp = requests.get(url, params=params, headers=headers, timeout=30)
print(f'Status: {resp.status_code}')
data = resp.json()
print(f'success: {data.get("success")}, errorCode: {data.get("errorCode")}')
value = data.get('value') or {}
print(f'sectionsNo999: {value.get("sectionsNo999")!r}')
print(f'sectionsNo1: {value.get("sectionsNo1")!r}')
print(f'isCancel: {value.get("isCancel")}')
print(f'matchResultList count: {len(value.get("matchResultList") or [])}')
if value.get('matchResultList'):
    for item in value['matchResultList'][:3]:
        print(item)
