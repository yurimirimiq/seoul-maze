"""한 장소의 약도 데이터 <장소>/map.js를 만든다.

쓰는 법: python3 make_map.py coex
새 장소 추가: 아래 PLACES에 항목을 하나 더 넣는다.

- 바깥 지도(건물, 길, 지하철 출구): 오픈스트리트맵에서 받는다. © OpenStreetMap contributors (ODbL)
- 실내(칸 모양, 가게 위치): <장소>/shapes.tsv, <장소>/poi.tsv를 읽는다. 둘은 공식 실내 지도의 좌표(1칸 = 10cm)로 적혀 있다.

장소는 두 가지다.
- bbox가 있는 곳(코엑스): 바깥 지도를 그리고 그 위에 실내를 돌리고 옮겨서 얹는다.
- frame이 있는 곳(잠실): 바깥 지도 없이 실내 지도만 그린다. 공식 실내 지도가 건물들을 실제 위치와 다르게 벌려 놓아서
  바깥 지도에 맞출 수 없을 때 쓴다.
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
        # 지하철 출구. OSM 지점(node) id -> ('○○역 N번 출구', 노선 번호). 출구 표지판으로 그려진다.
        "spots": {
            3404873904: ("삼성역 5·6번 출구", "2"),  # 5번 출구 위치. 6번은 바로 옆이라 한 점으로 표시
            3824607465: ("봉은사역 7번 출구", "9"),
        },
        # 실내 좌표를 바깥 지도에 얹는 값: (돌리는 각도, 가로 이동, 세로 이동).
        # 실내 자료에는 위도·경도가 없어서, 별마당도서관 건물과 눈에 띄는 가게 20여 곳의 실제 위치에 겹치게 맞췄다.
        # 맞춘 결과 북쪽 끝 가게는 봉은사역 7번 출구, 남동쪽 끝 맥도날드는 삼성역 5·6번 출구 옆에 온다. 오차는 대개 3~10m다.
        "poi_transform": (-114.24, 32.71, 110.69),
    },
    "gosok": {
        "bbox": (37.5018, 37.5090, 126.9995, 127.0105),
        # 지하상가(고투몰)는 땅 밑으로 길게 깔려 있어서 다른 건물 밑에 그려지게 맨 앞에 둔다
        "buildings": {
            1354860678: "고투몰(지하상가)",
            159117108: "신세계백화점",
            356127040: "센트럴시티(호남선)",
            309352819: "고속버스터미널(경부선)",
            593858530: "파미에스테이션",
            413372929: "뉴코아아울렛",
        },
        # 노선마다 귀퉁이 출구만 골랐다(3호선 1번, 7호선 3·5번, 9호선 8-1번). 다 넣으면 표지판끼리 겹친다.
        # 역 이름은 첫 출구 옆에 한 번만 쓰이므로, 주변이 비어 있는 5번 출구를 맨 앞에 둔다.
        "spots": {
            3146849639: ("고속터미널역 5번 출구", "7"),
            3146849471: ("고속터미널역 3번 출구", "7"),
            3146856929: ("고속터미널역 1번 출구", "3"),
            3146857129: ("고속터미널역 8-1번 출구", "9"),
        },
        # 지하상가(make_gotomall.py가 만든 칸 배치)를 바깥 지도에 얹는 값.
        # OSM의 '고속터미널 지하상가' 모양에 맞췄다: 기울기 -20.9도, A001 서쪽 끝이 그 모양의 긴 복도 서쪽 끝에 오게 했다.
        # 맞춘 뒤 6번 출입구는 반포쇼핑타운 2·3동 앞, 12번 출입구는 6·7동 앞에 와서 배치도의 안내 글과 맞는다.
        "poi_transform": (-20.9, 17.67, 44.28),
    },
    "jamsil": {
        # 실내 좌표에서 화면에 넣을 범위 (왼쪽, 위, 오른쪽, 아래)
        "frame": (284, 500, 15018, 7176),
        # 건물 이름표: 이름 -> 실내 좌표. 건물 덩어리 바로 위에 둔다.
        "labels": {"롯데백화점": (3789, 3480), "롯데월드몰": (11970, 3730), "캐슬플라자": (10779, 650)},
    },
}

WIDTH = 100  # 약도 가로 길이. 세로는 실제 비율대로 계산한다.
M_PER_LAT = 111_000
M_PER_LON = 88_300  # 서울 위도에서 경도 1도의 길이
# 큰길은 OSM에 양방향이 따로 그려져 있어서 한 줄의 너비만 적는다
ROAD_WIDTH_M = {"trunk": 18, "primary": 18, "secondary": 14, "tertiary": 10, "residential": 6, "unclassified": 6}


def outdoor(cfg):
    """오픈스트리트맵에서 바깥 지도를 받는다. (지도 데이터, 실내 좌표를 약도 좌표로 바꾸는 함수)를 돌려준다."""
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
        big = kind in ("trunk", "primary")  # 큰길은 색을 달리 칠하고 이름을 쓴다
        roads.append({"w": w, "big": big, "pts": line(e)})
        name = e["tags"].get("name")
        if name and big and not name.endswith(("고가도로", "지하도로", "지하차도")):  # 같은 길 위아래로 겹치는 구조물 이름은 뺀다
            pts = [xy(p["lat"], p["lon"]) for p in e["geometry"]]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                mx, my, length = (x1 + x2) / 2, (y1 + y2) / 2, math.hypot(x2 - x1, y2 - y1)
                if 8 < mx < WIDTH - 8 and 4 < my < height - 4 and length > names.get(name, {"len": 0})["len"]:
                    rot = math.degrees(math.atan2(y2 - y1, x2 - x1))
                    rot = rot - 180 if rot > 90 else rot + 180 if rot < -90 else rot  # 글자가 뒤집히지 않게
                    names[name] = {"len": length, "name": name, "x": round(mx, 1), "y": round(my, 1), "rot": round(rot)}
    roads.sort(key=lambda r: (r["w"], r["pts"]))

    spots = []
    for osm_id, (name, line) in cfg["spots"].items():
        x, y = xy(found[osm_id]["lat"], found[osm_id]["lon"])
        spots.append({"name": name, "x": x, "y": y, "line": line})

    deg, dx, dy = cfg.get("poi_transform", (0, 0, 0))  # 실내 자료가 없는 곳은 안 쓴다
    cos, sin, k = math.cos(math.radians(deg)), math.sin(math.radians(deg)), 0.1 / unit

    def indoor_xy(px, py):
        return k * (cos * px - sin * py) + dx, k * (sin * px + cos * py) + dy

    data = {"width": WIDTH, "height": height, "main": buildings[0]["name"], "roads": roads,
            "roadNames": [{k: v for k, v in n.items() if k != "len"} for _, n in sorted(names.items())],
            "blocks": blocks, "buildings": buildings, "spots": spots}
    return data, indoor_xy


def indoor_only(cfg):
    """바깥 지도 없이 실내 좌표의 한 범위를 약도 너비에 맞춘다."""
    left, top, right, bottom = cfg["frame"]
    k = WIDTH / (right - left)

    def indoor_xy(px, py):
        return (px - left) * k, (py - top) * k

    spots = [{"name": name, "x": round(indoor_xy(*at)[0], 2), "y": round(indoor_xy(*at)[1], 2)} for name, at in cfg["labels"].items()]
    data = {"width": WIDTH, "height": round((bottom - top) * k), "roads": [], "roadNames": [], "blocks": [], "buildings": [], "spots": spots}
    return data, indoor_xy


def main(place):
    cfg = PLACES[place]
    data, indoor_xy = outdoor(cfg) if "bbox" in cfg else indoor_only(cfg)
    spots = data["spots"]

    def rows(name):
        path = f"{place}/{name}"
        return [r.rstrip("\n").split("\t") for r in open(path, encoding="utf-8") if not r.startswith("#")] if os.path.exists(path) else []

    def place_xy(px, py):  # 가게 칸은 몇 m짜리라 소수 둘째 자리까지 남긴다
        x, y = indoor_xy(float(px), float(py))
        return round(x, 2), round(y, 2)

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
            if (floor, i) in named or item[0] in ("바닥", "바닥면", "빈곳", "기타"):
                continue
            if item[0] == "가게":
                item[0] = "기타"
                continue
            pts = [tuple(map(float, p.split(","))) for p in item[1].split()]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            spots.append({"name": item[0], "x": round((min(xs) + max(xs)) / 2, 2), "y": round((min(ys) + max(ys)) / 2, 2),
                          "floor": floor, "kind": "편의시설", "shape": i})
    for s in spots:
        assert 0 <= s["x"] <= WIDTH and 0 <= s["y"] <= data["height"], f"범위 밖: {s['name']}"

    data["shapes"] = shapes
    with open(f"{place}/map.js", "w", encoding="utf-8") as f:
        f.write("// make_map.py가 만든 파일. 손으로 고치지 말고 make_map.py를 다시 돌린다.\n")
        f.write("// 건물과 길: © OpenStreetMap contributors (ODbL). 실내: shapes.tsv, poi.tsv 참고.\n")
        f.write("const MAP = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace('},{', '},\n{') + ";\n")
    print(f"{place}/map.js 저장: 건물 {len(data['buildings'])}+{len(data['blocks'])}개, 길 {len(data['roads'])}개, "
          f"칸 {sum(map(len, shapes.values()))}개, 지점 {len(spots)}개, 크기 {WIDTH}x{data['height']}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PLACES:
        sys.exit(f"쓰는 법: python3 make_map.py <장소>\n장소: {', '.join(PLACES)}")
    main(sys.argv[1])
