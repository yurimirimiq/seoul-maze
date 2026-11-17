"""한 장소의 약도 데이터 <장소>/map.js를 만든다.

쓰는 법: python3 make_map.py coex
새 장소 추가: 아래 PLACES에 항목을 하나 더 넣는다.

- 건물, 길, 지하철 출구: 오픈스트리트맵에서 받는다. © OpenStreetMap contributors (ODbL)
- 실내 칸 모양과 가게 위치: <장소>/shapes.tsv, <장소>/poi.tsv가 있으면 읽어서 약도 좌표로 바꾼다.
"""
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PLACES = {
    "coex": {
        # 화면에 넣을 범위 (남, 북, 서, 동)
        "bbox": (37.5078, 37.5145, 127.0565, 127.0645),
        # 이름표를 붙일 건물. OSM 건물(way) id -> 화면에 쓸 이름. 첫 번째가 행사 위치의 기본값이다.
        "buildings": {
            74013220: "코엑스 전시장",
            74013224: "현대백화점",
            74056379: "트레이드타워",
            74056384: "아셈타워",
            74056386: "도심공항터미널",
            74056390: "인터컨티넨탈",
        },
        # OSM 지점(node) id -> 화면에 쓸 이름. '○○역 N번 출구' 꼴이면 출구 표지판으로 그려진다.
        "spots": {
            3404873904: "삼성역 5·6번 출구",  # 5번 출구 위치. 6번은 바로 옆이라 한 점으로 표시
            3824607465: "봉은사역 7번 출구",
        },
        # poi.tsv 좌표(1칸 = 10cm)를 약도에 얹는 값: (돌리는 각도, 가로 이동, 세로 이동).
        # poi.tsv에는 위도·경도가 없어서, 별마당도서관 건물과 눈에 띄는 가게 20여 곳의 실제 위치에 겹치게 맞췄다.
        # 맞춘 결과 북쪽 끝 가게는 봉은사역 7번 출구, 남동쪽 끝 맥도날드는 삼성역 5·6번 출구 옆에 온다. 오차는 대개 3~10m다.
        "poi_transform": (-114.24, 32.71, 110.69),
    },
}

WIDTH = 100  # 약도 가로 길이. 세로는 실제 비율대로 계산한다.
M_PER_LAT = 111_000
M_PER_LON = 88_300  # 서울 위도에서 경도 1도의 길이
# 큰길은 OSM에 양방향이 따로 그려져 있어서 한 줄의 너비만 적는다
ROAD_WIDTH_M = {"trunk": 18, "primary": 18, "secondary": 14, "tertiary": 10, "residential": 6, "unclassified": 6}


def main(place):
    cfg = PLACES[place]
    south, north, west, east = cfg["bbox"]
    unit = (east - west) * M_PER_LON / WIDTH  # 약도 1칸이 몇 m인지
    height = round((north - south) * M_PER_LAT / unit)

    def xy(lat, lon):
        return round((lon - west) * M_PER_LON / unit, 1), round((north - lat) * M_PER_LAT / unit, 1)

    def line(way):
        return " ".join("%s,%s" % xy(p["lat"], p["lon"]) for p in way["geometry"])

    box = f"({south},{west},{north},{east})"
    query = (f"[out:json][timeout:60];(way[building]{box};way[highway~'^({'|'.join(ROAD_WIDTH_M)})$']{box};"
             f"node(id:{','.join(map(str, cfg['spots']))}););out geom;")
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "make_map.py"})
    for attempt in range(4):  # 지도 서버가 502, 504를 자주 내서 몇 번 다시 해 본다
        try:
            elements = json.load(urllib.request.urlopen(req, timeout=90))["elements"]
            break
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 3:
                raise
            time.sleep(10)
    found = {e["id"]: e for e in elements}
    missing = (set(cfg["buildings"]) | set(cfg["spots"])) - set(found)
    assert not missing, f"OSM에서 못 찾은 id: {missing}"

    # 건물: 이름표를 붙일 것은 설정에 적은 순서대로, 나머지는 바탕으로만 그린다
    buildings = []
    for osm_id, name in cfg["buildings"].items():
        pts = [xy(p["lat"], p["lon"]) for p in found[osm_id]["geometry"]]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        buildings.append({"name": name, "x": round((min(xs) + max(xs)) / 2, 1), "y": round((min(ys) + max(ys)) / 2, 1),
                          "pts": " ".join(f"{x},{y}" for x, y in pts)})
    blocks = sorted(line(e) for e in elements
                    if e["type"] == "way" and "building" in e["tags"] and e["id"] not in cfg["buildings"])

    # 길: 넓은 길이 위에 오게 좁은 길부터 그린다. 큰길 이름은 가장 긴 구간 위에 길 방향으로 한 번만 쓴다.
    roads, names = [], {}
    for e in elements:
        kind = e.get("tags", {}).get("highway")
        if e["type"] != "way" or kind not in ROAD_WIDTH_M:
            continue
        w = round(ROAD_WIDTH_M[kind] / unit, 1)
        roads.append({"w": w, "pts": line(e)})
        name = e["tags"].get("name")
        if name and w >= 2.5:
            pts = [xy(p["lat"], p["lon"]) for p in e["geometry"]]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                mx, my, length = (x1 + x2) / 2, (y1 + y2) / 2, math.hypot(x2 - x1, y2 - y1)
                if 8 < mx < WIDTH - 8 and 4 < my < height - 4 and length > names.get(name, {"len": 0})["len"]:
                    rot = math.degrees(math.atan2(y2 - y1, x2 - x1))
                    rot = rot - 180 if rot > 90 else rot + 180 if rot < -90 else rot  # 글자가 뒤집히지 않게
                    names[name] = {"len": length, "name": name, "x": round(mx, 1), "y": round(my, 1), "rot": round(rot)}
    roads.sort(key=lambda r: (r["w"], r["pts"]))
    road_names = [{k: v for k, v in n.items() if k != "len"} for _, n in sorted(names.items())]

    spots = []
    for osm_id, name in cfg["spots"].items():
        x, y = xy(found[osm_id]["lat"], found[osm_id]["lon"])
        spots.append({"name": name, "x": x, "y": y})

    # 실내 칸과 가게: 공식 지도 좌표를 돌리고 옮겨서 약도 좌표로 바꾼다
    def rows(name):
        path = f"{place}/{name}"
        return [r.rstrip("\n").split("\t") for r in open(path, encoding="utf-8") if not r.startswith("#")] if os.path.exists(path) else []

    deg, dx, dy = cfg.get("poi_transform", (0, 0, 0))
    cos, sin, k = math.cos(math.radians(deg)), math.sin(math.radians(deg)), 0.1 / unit

    def place_xy(px, py):  # 가게 칸은 몇 m짜리라 소수 둘째 자리까지 남긴다
        px, py = float(px), float(py)
        return round(k * (cos * px - sin * py) + dx, 2), round(k * (sin * px + cos * py) + dy, 2)

    # shapes: 층 -> [[종류, 꼭짓점들], ...]. 파일에 적힌 순서(큰 것부터)대로 그려야 작은 칸이 위에 온다.
    shapes, index = {}, {}
    for floor, kind, shape_id, pts in rows("shapes.tsv"):
        index[shape_id] = (floor, len(shapes.setdefault(floor, [])))
        shapes[floor].append([kind, " ".join("%s,%s" % place_xy(*p.split(",")) for p in pts.split())])
    for floor, kind, name, px, py, shape_id in rows("poi.tsv"):
        x, y = place_xy(px, py)
        spot = {"name": name, "x": x, "y": y, "floor": floor, "kind": kind}
        if index.get(shape_id, [None])[0] == floor:
            spot["shape"] = index[shape_id][1]  # 그 층 shapes에서 이 가게가 차지한 칸의 번호
            if shapes[floor][spot["shape"]][0] == "가게":
                shapes[floor][spot["shape"]][0] = kind  # 칸을 가게 종류 색으로 칠할 수 있게
        spots.append(spot)
    # 이름이 안 붙은 칸 정리: 시설 칸(에스컬레이터 등)은 종류 이름을 가운데에 붙이고, 가게 칸은 빈 매장으로 보고 회색으로 돌린다
    named = {(s["floor"], s["shape"]) for s in spots if "shape" in s}
    for floor, items in shapes.items():
        for i, item in enumerate(items):
            if (floor, i) in named or item[0] in ("바닥", "기타"):
                continue
            if item[0] == "가게":
                item[0] = "기타"
                continue
            pts = [tuple(map(float, p.split(","))) for p in item[1].split()]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            spots.append({"name": item[0], "x": round((min(xs) + max(xs)) / 2, 2), "y": round((min(ys) + max(ys)) / 2, 2),
                          "floor": floor, "kind": "편의시설", "shape": i})
    for i in buildings + spots:
        assert 0 <= i["x"] <= WIDTH and 0 <= i["y"] <= height, f"범위 밖: {i['name']}"

    data = {"width": WIDTH, "height": height, "main": buildings[0]["name"], "roads": roads, "roadNames": road_names,
            "blocks": blocks, "buildings": buildings, "shapes": shapes, "spots": spots}
    os.makedirs(place, exist_ok=True)
    with open(f"{place}/map.js", "w", encoding="utf-8") as f:
        f.write("// make_map.py가 만든 파일. 손으로 고치지 말고 make_map.py를 다시 돌린다.\n")
        f.write("// 건물과 길: © OpenStreetMap contributors (ODbL). 가게 위치: poi.tsv 참고.\n")
        f.write("const MAP = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace('},{', '},\n{') + ";\n")
    print(f"{place}/map.js 저장: 건물 {len(buildings)}+{len(blocks)}개, 길 {len(roads)}개, 지점 {len(spots)}개, 크기 {WIDTH}x{height}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PLACES:
        sys.exit(f"쓰는 법: python3 make_map.py <장소>\n장소: {', '.join(PLACES)}")
    main(sys.argv[1])
