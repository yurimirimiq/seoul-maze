"""서울고속버스터미널(경부선 쪽 건물) 공식 층별 안내에서 가게 번호·이름과 안내 그림을 받아
gosok/terminal.shapes.tsv, terminal.poi.tsv, terminal.js를 만든다.

쓰는 법: python3 tools/make_terminal.py   (그다음 python3 tools/make_map.py gosok)
맥에서만 돈다. 그림 읽기와 글자 읽기는 make_shinsegae.py의 것을 그대로 쓴다.

공식 사이트(exterminal.co.kr)의 층별 안내는 층마다 번호가 찍힌 작은 약도 그림(626x422)과 "번호, 이름, 전화" 목록으로 되어 있다.
이름은 목록에서, 자리는 그림 속 번호 위치에서 얻는다. 전화번호는 받지 않는다.
그림은 축척이 없는 약도라서 건물 테두리에 맞춰 가로세로를 따로 늘렸다. 가게 순서와 대략의 자리만 맞고 20m쯤 어긋날 수 있다.
"""
import json
import os
import re
import subprocess
import tempfile
import urllib.request

from make_shinsegae import find_regions, outline, read_brightness, read_text, simplify

SITE = "https://www.exterminal.co.kr/"
SKIP = re.compile(r"^$|입점준비중|오피스|사무실|영업소")  # 가게가 아닌 칸
CELL = range(224, 241)  # 가게 칸의 밝기(231쯤). 통로는 흰색(255)이다.
OUTSIDE = range(186, 201)  # 그림 바탕의 회색(194)과 옆 건물을 흐리게 그린 곳(188쯤)

# 건물 자리. 고투몰과 같은 실내 좌표(10cm 단위, x 동쪽, y 남쪽)이고 OSM 건물 테두리에서 읽었다.
# 본관(승차홈 1~16): x 3061~3823, y 642~2200. 별관(승차홈 17~46): 본관 북쪽 끝에서 동쪽으로 x 6235까지, y 640~945.
# 축 하나는 ((그림 px, 실내 좌표), (그림 px, 실내 좌표)) 두 점으로 적는다. 그림에서 벽이 놓인 px는 눈으로 읽었다.
# 본관 그림은 위가 서쪽이다(위에 '호남선'이라고 적혀 있다). 그래서 그림의 가로가 실내의 남북(turn)이다. 별관 그림은 위가 북쪽이다.
# hand: 글자 인식이 못 읽은 번호의 자리를 그림을 보고 적은 것 {번호: (px, px)}.
MAIN, SUB = "고속버스터미널 본관 가게", "고속버스터미널 별관 가게"
PLANS = [
    dict(floor="1", cat=MAIN, page="include/floor.asp?floornum=", block="finfo2", image="n_floor011.jpg", turn=True,
         h=((58, 2200), (612, 642)), v=((112, 3061), (300, 3823)), hand={1: (131, 158), 2: (173, 131), 13: (527, 217)}),
    dict(floor="B1", cat=MAIN, page="include/floor.asp?floornum=", block="finfo1", image="n_floorb01.jpg", turn=True,
         h=((72, 2200), (590, 642)), v=((118, 3061), (322, 3823)), hand={}),
    dict(floor="1", cat=SUB, page="include/floor_sub.asp?floornum=", block="finfo2", image="n_floorf1_sub.jpg", turn=False,
         h=((40, 3823), (605, 6235)), v=((100, 640), (245, 945)), hand={43: (228, 136), 56: (462, 188), 57: (473, 188)}),
    dict(floor="2", cat=SUB, page="include/floor_sub.asp?floornum=", block="finfo3", image="n_floorf2_sub.jpg", turn=False,
         h=((65, 3823), (615, 6235)), v=((120, 640), (285, 945)), hand={1: (33, 205), 5: (184, 205), 8: (245, 205)}),
    # 별관 지하는 본관 북쪽 끝 위로도 뻗어 있고(그림 왼쪽), 지하상가로 가는 통로가 건물 북쪽 밖으로 나와 있다
    dict(floor="B1", cat=SUB, page="include/floor_sub.asp?floornum=", block="finfo1", image="n_floorb01_sub.jpg", turn=False,
         h=((115, 3823), (615, 6235)), v=((210, 640), (298, 945)),
         hand={32: (30, 157), 33: (113, 157), 34: (178, 190), 35: (152, 247), 36: (196, 247), 37: (213, 247), 38: (222, 247), 39: (231, 247),
               40: (240, 247), 41: (283, 216), 42: (295, 216), 43: (306, 216), 44: (317, 216), 45: (328, 216), 46: (584, 219)}),
]


def fetch(path):
    return urllib.request.urlopen(urllib.request.Request(SITE + path, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()


def names_in(html, block):
    """목록 페이지에서 한 층의 {번호: 이름}."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    part = html.split(f"<div id={block} ", 1)[1].split("<div id=finfo", 1)[0]
    found = re.findall(r'<span class="num">\s*(\d+)\s*</span>\s*<b>(.*?)</b>', part, flags=re.S)
    return {int(n): re.sub(r"\s+", " ", re.sub(r"<[^>]+>|&nbsp;", "", name)).strip() for n, name in found}


def numbers(text, wanted):
    """글자 한 줄에 적힌 번호들. 나란한 칸의 번호가 '17 16'이나 '5657'처럼 한 줄로 읽히기도 해서 나눈다."""
    if not re.fullmatch(r"[\d\s]+", text):
        return []
    return [int(n) for t in text.split() for n in ([t[:2], t[2:]] if len(t) == 4 and int(t) not in wanted else [t])]


def place(plan, px, py):
    """그림의 한 점을 실내 좌표로. 축마다 두 점을 잇는 직선으로 옮긴다."""
    (a0, b0), (a1, b1) = plan["h"]
    (c0, d0), (c1, d1) = plan["v"]
    along, down = b0 + (px - a0) * (b1 - b0) / (a1 - a0), d0 + (py - c0) * (d1 - d0) / (c1 - c0)
    return (round(down), round(along)) if plan["turn"] else (round(along), round(down))


def self_check():
    assert numbers("17 16", {16, 17}) == [17, 16] and numbers("5657", {56, 57}) == [56, 57] and numbers("매표소", {1}) == []
    assert place(PLANS[0], 58, 112) == (3061, 2200) and place(PLANS[0], 612, 300) == (3823, 642)  # 본관: 왼쪽 위 = 남서, 오른쪽 아래 = 북동
    assert place(PLANS[2], 40, 100) == (3823, 640) and place(PLANS[2], 605, 245) == (6235, 945)   # 별관: 왼쪽 위 = 북서
    assert names_in('<div id=finfo2 class="f"><li><span class="num">7</span><b>파리바게트</b>&nbsp;02)1</li><div id=finfo1 >', "finfo2") == {7: "파리바게트"}


def main():
    self_check()
    shapes, pois, stores, report = [], [], {}, []
    pages = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, plan in enumerate(PLANS):
            if plan["page"] not in pages:
                pages[plan["page"]] = fetch(plan["page"]).decode("utf-8", "replace")
            names = {n: name for n, name in names_in(pages[plan["page"]], plan["block"]).items() if not SKIP.search(name)}
            small, big = os.path.join(tmp, f"{i}.jpg"), os.path.join(tmp, f"{i}.png")
            open(small, "wb").write(fetch("images/" + plan["image"]))
            subprocess.run(["sips", "-Z", "2504", "-s", "format", "png", small, "--out", big], check=True, capture_output=True)  # 번호 글자가 작아서 4배로 키워 읽는다
            w, h, light = read_brightness(small)
            xy = lambda pts: " ".join("%d,%d" % place(plan, x, y) for x, y in pts)
            key = f"t{i}"

            # 바닥: 그림 바탕이 아닌 곳 가운데 큰 덩어리가 건물이다(제목 글자와 아래 띠는 그보다 작다). 칸보다 먼저 적어야 밑에 깔린다.
            floor_label, floor_regions = find_regions(w, h, light.translate(bytes(v not in OUTSIDE for v in range(256))))
            building = {n for n, (area, _) in floor_regions.items() if area >= 20000}
            for n in building:
                shapes.append((plan["floor"], "바닥면", f"{key}-floor{n}", xy(simplify(outline(w, h, floor_label, n, floor_regions[n][1]), 1))))
            label, regions = find_regions(w, h, light.translate(bytes(v in CELL for v in range(256))))
            regions = {n: v for n, v in regions.items() if v[0] >= 60 and floor_label[v[1]] in building}  # 건물 안의 칸만

            # 번호 자리: 글자 인식으로 읽고, 못 읽은 것은 손으로 적은 자리를 쓴다
            at = {}
            (a0, _), (a1, _) = plan["h"]
            (c0, _), (c1, _) = plan["v"]
            for x, y, bw, bh, _, text in read_text(big):
                found = numbers(text, names)
                for j, n in enumerate(found):
                    px, py = (x + bw * (j + .5) / len(found)) * w, (y + bh / 2) * h
                    if a0 - 8 <= px <= a1 + 8 and c0 - 8 <= py <= c1 + 8:  # 건물 벽 밖의 숫자(승차홈 번호)는 가게 번호가 아니다
                        at.setdefault(n, (px, py))
            at.update(plan["hand"])
            owner = {}
            for n, (px, py) in at.items():
                near = [label[int(py + dy) * w + int(px + dx)] for dx, dy in ((0, 0), (-7, 0), (7, 0), (0, -7), (0, 7)) if 0 <= px + dx < w and 0 <= py + dy < h]
                room = max(set(near) & set(regions), key=near.count, default=0)
                if n in names:
                    pois.append((plan["floor"], plan["cat"], names[n], *map(str, place(plan, px, py)), f"{key}-{room}" if room else ""))
                    owner[room] = n
            for n, (area, start) in sorted(regions.items(), key=lambda r: -r[1][0]):
                pts = simplify(outline(w, h, label, n, start), 1)
                if len(pts) >= 3:
                    shapes.append((plan["floor"], "가게" if n in owner else "기타", f"{key}-{n}", xy(pts)))
            listed = stores.setdefault(plan["floor"], {}).setdefault(plan["cat"], [])
            listed += [name for name in names.values() if name not in listed]
            lost = sorted(set(names) - set(at))
            report.append(f"{plan['cat']} {plan['floor']}층: 가게 {len(names)}곳, 자리 찾은 번호 {len(names) - len(lost)}개" + (f", 못 찾은 번호 {lost}" if lost else ""))

    head = "# make_terminal.py가 만든 파일. 손으로 고치지 말고 make_terminal.py를 고쳐서 다시 돌린다.\n# 서울고속버스터미널 공식 층별 안내(exterminal.co.kr)의 약도 그림과 가게 목록에서 만들었다. 좌표는 고투몰(shapes.tsv)과 같은 틀이다.\n# 그림이 축척 없는 약도라 건물 테두리에 맞춰 늘린 것이다. 20m쯤 어긋날 수 있다.\n"
    with open("gosok/terminal.shapes.tsv", "w", encoding="utf-8") as f:
        f.write(head + "# 층\t종류\tid\t꼭짓점들\n")
        f.writelines("\t".join(s) + "\n" for s in shapes)
    with open("gosok/terminal.poi.tsv", "w", encoding="utf-8") as f:
        f.write(head + "# 층\t종류\t이름\tx\ty\t자리\n")
        f.writelines("\t".join(p) + "\n" for p in pois)
    with open("gosok/terminal.js", "w", encoding="utf-8") as f:
        f.write("// make_terminal.py가 만든 파일. 손으로 고치지 않는다.\n")
        f.write("// 서울고속버스터미널 공식 층별 안내(exterminal.co.kr)의 가게 이름. stores.js의 목록에 층별로 보탠다. 사무실과 빈 칸은 뺐다.\n")
        f.write("for (const [floor, more] of Object.entries(" + json.dumps(stores, ensure_ascii=False, indent=1) + ")) Object.assign(STORES[floor] ||= {}, more);\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
