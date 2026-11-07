"""Download high-resolution licensed car photos for an offline DriveMatch demo.
Uses the public Wikimedia Commons API. Run with internet access from project root:
    py scripts/download_car_photos.py
Photos and corresponding source/attribution links are saved in frontend/public.
Review photos manually before a presentation: some cars have multiple generations.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
CARS=json.loads((ROOT/'backend/cars.json').read_text(encoding='utf-8'))
OUT=ROOT/'frontend/public/car-images'
MANIFEST=ROOT/'frontend/public/car-photos.json'
OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}
HEADERS={'User-Agent':'DriveMatchUniversityProject/1.0 (educational car image attribution)'}

def fetch(url):
    with urlopen(Request(url,headers=HEADERS),timeout=25) as response:
        return response.read()

def norm(s):
    return re.sub('[^a-z0-9]+',' ',s.lower()).strip()

def rank(page,car):
    info=(page.get('imageinfo') or [{}])[0]
    title=norm(page.get('title','').removeprefix('File:'))
    words=title.split()
    if not all(w in words for w in norm(car['brand']+' '+car['model']).split()):return -100
    if info.get('width',0)<640 or info.get('height',0)<320:return -100
    ratio=info['width']/info['height']
    if not 1.2<ratio<3.1:return -100
    score=50
    if any(w in title for w in ('front','side','exterior','sedan','hatchback','suv')):score+=14
    if any(w in title for w in ('interior','dashboard','engine','wheel','logo','emblem','police','taxi','advert')):score-=55
    if re.search(r'202[0-9]',title):score+=5
    score+=max(0,9-abs(ratio-1.75)*12)
    return score

def find_photo(car):
    for suffix in (' automobile',''):
        qs=urlencode({'action':'query','format':'json','generator':'search','gsrsearch':f"filetype:bitmap {car['brand']} {car['model']}{suffix}",'gsrnamespace':6,'gsrlimit':30,'prop':'imageinfo','iiprop':'url|size|mime|extmetadata','iiurlwidth':1100})
        result=json.loads(fetch('https://commons.wikimedia.org/w/api.php?'+qs))
        pages=list(result.get('query',{}).get('pages',{}).values())
        scored=sorted(((rank(p,car),p) for p in pages),key=lambda x:x[0],reverse=True)
        if scored and scored[0][0]>45:return scored[0][1]
    return None

for number,car in enumerate(CARS,1):
    key=str(car['id'])
    if key in manifest:
        print(f'[{number}/{len(CARS)}] Already downloaded: {car["brand"]} {car["model"]}')
        continue
    try:
        page=find_photo(car)
        if not page:
            print(f'[{number}/{len(CARS)}] No confirmed exterior image: {car["brand"]} {car["model"]}')
            continue
        info=page['imageinfo'][0]
        mime=info.get('mime','')
        ext='.png' if mime=='image/png' else '.webp' if mime=='image/webp' else '.jpg'
        target=OUT/(key+ext)
        target.write_bytes(fetch(info['thumburl']))
        meta=info.get('extmetadata') or {}
        # Preserve source URL and author information for review and credit.
        author=re.sub('<[^>]+>','',meta.get('Artist',{}).get('value','')).strip()
        manifest[key]={'url':f'/car-images/{target.name}','source':info.get('descriptionurl',''),'credit':('Photo: '+author[:55]) if author else 'Photo: Wikimedia Commons','license':meta.get('LicenseShortName',{}).get('value',''), 'file_title':page['title']}
        MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(f'[{number}/{len(CARS)}] Downloaded {car["brand"]} {car["model"]}')
    except Exception as exc:
        print(f'[{number}/{len(CARS)}] Failed: {car["brand"]} {car["model"]}: {exc}')
    time.sleep(0.5)
print(f'Complete: {len(manifest)} credited photos saved. Review the images before presenting.')
