# -*- coding: utf-8 -*-
"""삼삼엠투(33m2) 이대역·신촌역 월 30~50만원 매물을 수집해 index.html 을 다시 만든다.
사용: python crawl.py [출력경로]   (기본 index.html)
실패(수집 0건·비정상 급감) 시 기존 파일을 건드리지 않고 비정상 종료한다."""
import requests, json, sys, os, datetime, time

OUT = sys.argv[1] if len(sys.argv) > 1 else 'index.html'
HERE = os.path.dirname(os.path.abspath(__file__))
H = {'User-Agent': 'Mozilla/5.0', 'os-type': 'WEB', 'Client-Language': 'ko',
     'Origin': 'https://web.33m2.co.kr', 'Referer': 'https://web.33m2.co.kr/guest/search'}
STATIONS = [('이대역', 37.55673, 126.94601), ('신촌역', 37.55513, 126.93692)]
LO, HI = 300000, 500000
MIN_EXPECT = 30            # 이보다 적으면 API 이상으로 보고 갱신하지 않음

def get(url, **kw):
    for i in range(4):
        try:
            r = requests.get(url, headers=H, timeout=30, **kw)
            if r.status_code == 200: return r.json()['data']
            err = r.status_code
        except Exception as e:
            err = e
        time.sleep(2 * (i + 1))
    raise RuntimeError(f'요청 실패 {url} {err}')

found = {}
for kw, lat, lng in STATIONS:
    for page in range(1, 30):
        data = get('https://web.33m2.co.kr/v1/map/rooms', params={
            'keyword': kw, 'zoomLevel': 15, 'roomMarkerLat': lat, 'roomMarkerLng': lng,
            'swLat': 37.53, 'neLat': 37.58, 'swLng': 126.91, 'neLng': 126.97,
            'size': 100, 'page': page, 'sortBy': 'low_price'})
        for x in data['content']:
            if LO <= x['usingFee'] <= HI:
                x['_station'] = kw; found.setdefault(x['rid'], x)
        if data['last']: break
    else:
        raise RuntimeError('pagination did not terminate')

rows = []
for x in found.values():
    d = get(f"https://web.33m2.co.kr/v1/rooms/{x['rid']}")
    rows.append({
        'id': d['rid'], 'title': d['roomName'], 'price': d['usingFee'], 'fee': d.get('mgmtFee'),
        'deposit': d.get('deposit'), 'clean': d.get('cleanFee'), 'minweeks': d.get('minimumContractWeeks'),
        'address': d.get('addrStreet'), 'province': d.get('province'), 'town': d.get('town'),
        'type': d.get('propertyType'), 'area': d.get('pyeongSize'), 'rooms': d.get('roomCnt'),
        'baths': d.get('bathroomCnt'), 'lat': d.get('lat'), 'lng': d.get('lng'),
        'stations': d.get('subwayStations') or [x['_station']],
        'url': d.get('roomUrl') or f"https://web.33m2.co.kr/guest/room/{d['rid']}",
        'image': (d.get('pictures') or [None])[0], 'desc': d.get('description') or '',
        'management': d.get('managementFeeDescription') or '',
        'propertyLabel': x.get('propertyType')})
    time.sleep(0.15)
rows.sort(key=lambda r: (r['price'], r['id']))
print('collected', len(rows))
if len(rows) < MIN_EXPECT:
    sys.exit(f'수집 {len(rows)}건 < {MIN_EXPECT}: 이상 응답으로 보고 갱신하지 않습니다')

kst = datetime.timezone(datetime.timedelta(hours=9))
when = datetime.datetime.now(kst).strftime('%Y-%m-%d %H:%M')
tpl = open(os.path.join(HERE, 'template.html'), encoding='utf8', newline='').read()
js = json.dumps(rows, ensure_ascii=False).replace('</', '<\/')
html = tpl.replace('__ROOMS__', js).replace('__N__', str(len(rows))).replace('__WHEN__', when + ' (KST)')
open(OUT, 'w', encoding='utf8', newline='').write(html)
json.dump(rows, open(os.path.join(HERE, 'rooms.json'), 'w', encoding='utf8'), ensure_ascii=False)
print('wrote', OUT, len(html), 'bytes')
