import json

for fname in ['debug_api_crs_2026-07-25.json', 'debug_api_crs_2040613.json']:
    print(f'\n=== {fname} ===')
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            data = json.load(f)
        value = data['value']
        print('totalCount:', value.get('totalCount'))
        print('matchDateList:', value.get('matchDateList'))
        for mi in value.get('matchInfoList', []):
            print(f"businessDate: {mi.get('businessDate')}, subMatchList count: {len(mi.get('subMatchList', []))}")
            for m in mi.get('subMatchList', [])[:3]:
                print(f"  {m.get('matchNum')} {m.get('matchId')}: {m.get('homeTeamAbbName')} VS {m.get('awayTeamAbbName')}")
    except Exception as e:
        print(f'Error: {e}')
