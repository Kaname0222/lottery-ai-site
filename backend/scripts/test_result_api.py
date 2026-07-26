import requests
from datetime import datetime, timedelta

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.lottery.gov.cn/',
    'Origin': 'https://www.lottery.gov.cn',
}

url = 'https://webapi.sporttery.cn/gateway/uniform/football/getUniformMatchResultV1.qry'
all_matches = []
page = 1
while page <= 10:
    params = {
        'matchBeginDate': start_date,
        'matchEndDate': end_date,
        'matchPage': page,
        'pcOrWap': 0,
        'leagueId': '',
    }
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    data = resp.json()
    success = data.get('success')
    value = data.get('value') or {}
    matches = value.get('matchResult') or []
    total_pages = value.get('pages') or 1
    match_nums = [m.get('matchNumStr') for m in matches]
    print(f'page {page}: success={success}, matches={len(matches)}, total_pages={total_pages}, nums={match_nums}')
    all_matches.extend(matches)
    page += 1

print(f'Total matches fetched: {len(all_matches)}')
print('All matchNumStr:', sorted(set(m.get('matchNumStr') for m in all_matches)))

for m in all_matches:
    if m.get('matchNumStr') in ['周日210', '周日211', '周日212', '周日213', '周日214', '周日215', '周日216', '周日217', '周日218']:
        print(f"{m.get('matchNumStr')} {m.get('homeTeam')} vs {m.get('awayTeam')}: sectionsNo1={m.get('sectionsNo1')!r} sectionsNo999={m.get('sectionsNo999')!r} poolStatus={m.get('poolStatus')!r} matchResultStatus={m.get('matchResultStatus')!r}")
