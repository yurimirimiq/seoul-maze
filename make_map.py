"""오픈스트리트맵에서 코엑스 일대 건물 윤곽과 주요 지점을 받아 map.js를 만든다.

쓰는 법: python3 make_map.py
지도 데이터 출처: © OpenStreetMap contributors (ODbL)
"""
import json
import urllib.parse
import urllib.request

# 화면에 넣을 범위 (위도, 경도)
SOUTH, NORTH, WEST, EAST = 37.5078, 37.5145, 127.0565, 127.0645
WIDTH = 100  # 약도 가로 길이. 세로는 실제 비율대로 계산한다.

# OSM 건물(way) id -> (화면에 쓸 이름, 이름표를 붙일지)
BUILDINGS = {
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
}
# OSM 지점(node) id -> 화면에 쓸 이름
SPOTS = {
    3404873904: "삼성역 5·6번 출구",  # 5번 출구 위치. 6번은 바로 옆이라 한 점으로 표시
    3824607465: "봉은사역 7번 출구",
    2676488130: "아쿠아리움",
    3453733093: "메가박스",
}

M_PER_LAT = 111_000
M_PER_LON = 88_300  # 서울 위도에서 경도 1도의 길이
UNIT = (EAST - WEST) * M_PER_LON / WIDTH  # 약도 1칸이 몇 m인지
HEIGHT = round((NORTH - SOUTH) * M_PER_LAT / UNIT)


def xy(lat, lon):
    return round((lon - WEST) * M_PER_LON / UNIT, 1), round((NORTH - lat) * M_PER_LAT / UNIT, 1)


def main():
    query = "[out:json][timeout:60];(way(id:%s);node(id:%s););out geom;" % (
        ",".join(map(str, BUILDINGS)), ",".join(map(str, SPOTS)))
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "make_map.py"})
    elements = json.load(urllib.request.urlopen(req, timeout=90))["elements"]

    buildings, spots = [], []
    for e in elements:
        if e["type"] == "way":
            name, label = BUILDINGS[e["id"]]
            pts = [xy(p["lat"], p["lon"]) for p in e["geometry"]]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            buildings.append({
                "name": name, "label": label,
                "x": round((min(xs) + max(xs)) / 2, 1), "y": round((min(ys) + max(ys)) / 2, 1),
                "pts": " ".join(f"{x},{y}" for x, y in pts)})
        else:
            x, y = xy(e["lat"], e["lon"])
            spots.append({"name": SPOTS[e["id"]], "x": x, "y": y})

    missing = (set(v[0] for v in BUILDINGS.values()) | set(SPOTS.values())) - {i["name"] for i in buildings + spots}
    assert not missing, f"OSM에서 못 찾음: {missing}"
    for i in buildings + spots:
        assert 0 <= i["x"] <= WIDTH and 0 <= i["y"] <= HEIGHT, f"범위 밖: {i['name']}"

    data = {"width": WIDTH, "height": HEIGHT, "buildings": buildings, "spots": spots}
    with open("map.js", "w", encoding="utf-8") as f:
        f.write("// make_map.py가 만든 파일. 손으로 고치지 말고 make_map.py를 다시 돌린다.\n")
        f.write("// 지도 데이터: © OpenStreetMap contributors (ODbL)\n")
        f.write("const MAP = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print(f"map.js 저장: 건물 {len(buildings)}개, 지점 {len(spots)}개, 크기 {WIDTH}x{HEIGHT}")


if __name__ == "__main__":
    main()
