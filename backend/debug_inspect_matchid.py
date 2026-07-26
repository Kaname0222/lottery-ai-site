import json

with open('debug_api_detail__uniform_football_getMatchCalculatorV1.qry_2040613.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
value = data['value']
print('value keys:', list(value.keys()))
print('totalCount:', value.get('totalCount'))
print('matchDateList:', value.get('matchDateList'))

found = False
for mi in value.get('matchInfoList', []):
    for m in mi.get('subMatchList', []):
        if str(m.get('matchId')) == '2040613':
            print('FOUND 2040613:')
            print(json.dumps(m, ensure_ascii=False, indent=2)[:5000])
            found = True
            break
    if found:
        break
if not found:
    print('2040613 not found in response')
    for mi in value.get('matchInfoList', []):
        print(f"businessDate: {mi.get('businessDate')}, subMatchList count: {len(mi.get('subMatchList', []))}")
        for m in mi.get('subMatchList', [])[:5]:
            print(f"  {m.get('matchNum')} {m.get('matchId')}: {m.get('homeTeamAbbName')} VS {m.get('awayTeamAbbName')}")
