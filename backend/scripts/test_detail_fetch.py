from app.services.scraper.result_scraper import fetch_match_result

mids = ['2040632', '2040633', '2040634', '2040635', '2040636', '2040637', '2040638', '2040639', '2040640']
for mid in mids:
    result = fetch_match_result(mid)
    print(f'{mid}: {result}')
