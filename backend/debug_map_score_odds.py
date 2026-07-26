import json

with open('debug_api_crs_default.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 找到周日202 (matchId 2040624)
target_mid = '2040624'
found = None
for mi in data['value']['matchInfoList']:
    for m in mi.get('subMatchList', []):
        if str(m.get('matchId')) == target_mid:
            found = m
            break
    if found:
        break

if not found:
    print(f'{target_mid} not found')
else:
    print(f"Match: {found.get('matchNum')} {found.get('homeTeamAbbName')} VS {found.get('awayTeamAbbName')}")
    crs = found.get('crs', {})
    print('\nCRS keys:')
    for k, v in crs.items():
        print(f'  {k}: {v}')
