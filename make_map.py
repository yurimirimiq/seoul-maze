"""오픈스트리트맵에서 한 장소의 건물 윤곽과 주요 지점을 받아 <장소>/map.js를 만든다.

쓰는 법: python3 make_map.py coex
새 장소 추가: 아래 PLACES에 항목을 하나 더 넣는다.
지도 데이터 출처: © OpenStreetMap contributors (ODbL)
"""
import json
import os
import sys
import urllib.parse
import urllib.request

PLACES = {
    "coex": {
        # 화면에 넣을 범위 (남, 북, 서, 동)
        "bbox": (37.5078, 37.5145, 127.0565, 127.0645),
        # OSM 건물(way) id -> (화면에 쓸 이름, 이름표를 붙일지). 첫 번째가 행사 위치의 기본값이다.
        "buildings": {
            74013220: ("코엑스 전시장", True),
            837196099: ("별마당도서관", True),
            74013224: ("현대백화점", True),
            74056379: ("트레이드타워", True),
            74056384: ("아셈타워", True),
            74056386: ("도심공항터미널", True),
            74056390: ("인터컨티넨탈", True),
            74056399: ("밀레니엄 광장", True),
            74056393: ("웨스틴 파르나스", False),  # 이름표가 메가박스와 겹쳐서 뺌
            837196098: ("파르나스타워", False),
            74056387: ("아티움", False),
            74056381: ("도심공항타워", False),
            74056398: ("오크우드", False),
            884138635: ("세븐럭 카지노", False),
        },
        # OSM 지점(node) id -> 화면에 쓸 이름. '○○역 N번 출구' 꼴이면 출구 표지판으로 그려진다.
        "spots": {
            3404873904: "삼성역 5·6번 출구",  # 5번 출구 위치. 6번은 바로 옆이라 한 점으로 표시
            3824607465: "봉은사역 7번 출구",
            2676488130: "아쿠아리움",
            3453733093: "메가박스",
        },
    },
}

WIDTH = 100  # 약도 가로 길이. 세로는 실제 비율대로 계산한다.
M_PER_LAT = 111_000
M_PER_LON = 88_300  # 서울 위도에서 경도 1도의 길이


def main(place):
    cfg = PLACES[place]
    south, north, west, east = cfg["bbox"]
    unit = (east - west) * M_PER_LON / WIDTH  # 약도 1칸이 몇 m인지
    height = round((north - south) * M_PER_LAT / unit)

    def xy(lat, lon):
        return round((lon - west) * M_PER_LON / unit, 1), round((north - lat) * M_PER_LAT / unit, 1)

    query = "[out:json][timeout:60];(way(id:%s);node(id:%s););out geom;" % (
        ",".join(map(str, cfg["buildings"])), ",".join(map(str, cfg["spots"])))
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "make_map.py"})
    found = {e["id"]: e for e in json.load(urllib.request.urlopen(req, timeout=90))["elements"]}
    missing = (set(cfg["buildings"]) | set(cfg["spots"])) - set(found)
    assert not missing, f"OSM에서 못 찾은 id: {missing}"

    buildings, spots = [], []
    for osm_id, (name, label) in cfg["buildings"].items():  # 설정에 적은 순서대로 저장해 결과가 매번 같게 한다
        pts = [xy(p["lat"], p["lon"]) for p in found[osm_id]["geometry"]]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        buildings.append({
            "name": name, "label": label,
            "x": round((min(xs) + max(xs)) / 2, 1), "y": round((min(ys) + max(ys)) / 2, 1),
            "pts": " ".join(f"{x},{y}" for x, y in pts)})
    for osm_id, name in cfg["spots"].items():
        x, y = xy(found[osm_id]["lat"], found[osm_id]["lon"])
        spots.append({"name": name, "x": x, "y": y})
    for i in buildings + spots:
        assert 0 <= i["x"] <= WIDTH and 0 <= i["y"] <= height, f"범위 밖: {i['name']}"

    data = {"width": WIDTH, "height": height, "main": buildings[0]["name"], "buildings": buildings, "spots": spots}
    os.makedirs(place, exist_ok=True)
    with open(f"{place}/map.js", "w", encoding="utf-8") as f:
        f.write("// make_map.py가 만든 파일. 손으로 고치지 말고 make_map.py를 다시 돌린다.\n")
        f.write("// 지도 데이터: © OpenStreetMap contributors (ODbL)\n")
        f.write("const MAP = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print(f"{place}/map.js 저장: 건물 {len(buildings)}개, 지점 {len(spots)}개, 크기 {WIDTH}x{height}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PLACES:
        sys.exit(f"쓰는 법: python3 make_map.py <장소>\n장소: {', '.join(PLACES)}")
    main(sys.argv[1])
