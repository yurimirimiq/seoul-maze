"""스타필드 공식 층별 안내에서 매장 이름을 받아 <장소>/stores.js를 만든다.

쓰는 법: python3 make_stores.py coex
매장이 바뀌었을 때 다시 돌리면 된다. 이름과 종류만 가져오고 전화번호, 사진, 도면은 가져오지 않는다.
"""
import datetime
import html
import json
import re
import sys
import time
import urllib.request

PLACES = {
    "coex": {
        "name": "스타필드 코엑스몰",
        "url": "https://www.starfield.co.kr/coexmall/tenant/floorInfo.do?floor=",
        # 공식 사이트의 층 이름 -> 우리 화면의 층 id (floors.js의 id와 같아야 한다)
        "floors": {"2F": "2", "1F": "1", "B1": "B1", "B2": "B2"},
    },
}


def main(place):
    cfg = PLACES[place]
    stores = {}
    for theirs, ours in cfg["floors"].items():
        req = urllib.request.Request(cfg["url"] + theirs, headers={"User-Agent": "Mozilla/5.0 (make_stores.py)"})
        page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        cats = {}
        for box in page.split('<div class="store-box-list')[1:]:
            head = re.search(r'<h4 class="tit">(.*?)<em>\((\d+)\)</em>', box, re.S)
            if not head:
                continue
            names = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()
                     for t in re.findall(r'<p class="tit">(.*?)</p>', box.split("</ul>")[0], re.S)]
            # 사이트가 적어 둔 개수와 다르면 페이지 구조가 바뀐 것이다
            assert len(names) == int(head.group(2)), f"{theirs} {head.group(1)}: {len(names)}개 읽음, 사이트는 {head.group(2)}개"
            cats[html.unescape(head.group(1)).strip()] = names
        assert cats, f"{theirs}: 매장을 하나도 못 읽었다. 페이지 구조가 바뀌었는지 확인한다."
        stores[ours] = cats
        time.sleep(1)  # 사이트에 부담을 주지 않게 천천히 받는다

    total = sum(len(n) for cats in stores.values() for n in cats.values())
    with open(f"{place}/stores.js", "w", encoding="utf-8") as f:
        f.write("// make_stores.py가 만든 파일. 손으로 고치지 말고 make_stores.py를 다시 돌린다.\n")
        f.write(f"// 출처: {cfg['name']} 공식 층별 안내, {datetime.date.today()} 확인\n")
        f.write("// 층 id -> 종류 -> 매장 이름들\n")
        f.write("const STORES = {\n")
        for floor, cats in stores.items():
            f.write(f" {json.dumps(floor)}: {{\n")
            for cat, names in cats.items():
                f.write(f"  {json.dumps(cat, ensure_ascii=False)}: {json.dumps(names, ensure_ascii=False)},\n")
            f.write(" },\n")
        f.write("};\n")
    print(f"{place}/stores.js 저장: {len(stores)}개 층, 매장 {total}곳")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PLACES:
        sys.exit(f"쓰는 법: python3 make_stores.py <장소>\n장소: {', '.join(PLACES)}")
    main(sys.argv[1])
