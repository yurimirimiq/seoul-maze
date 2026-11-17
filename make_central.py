"""공공데이터(소상공인시장진흥공단 상가(상권)정보)에서 센트럴시티와 파미에스테이션의 가게 이름과 층을 뽑아 gosok/central.js를 만든다.

쓰는 법: python3 make_central.py <받은 zip 파일>
zip은 공공데이터포털의 '소상공인시장진흥공단_상가(상권)정보'(https://www.data.go.kr/data/15083033/fileData.do)에서 받는다.
이용허락범위 제한이 없는 자료이고 330MB쯤이다. 저장소에는 넣지 않는다.

센트럴시티 공식 사이트가 열리지 않아서 이 자료를 쓴다. 알아 둘 한계:
- 실내 자리는 없다. 이름과 층만 있어서 화면에서는 목록과 검색에만 나온다.
- 이름이 간판이 아니라 사업자 등록 이름이다("○○센트럴시티점"처럼 길거나 회사 이름이 붙어 있다). 없어진 가게가 섞여 있을 수 있다.
- 같은 주소(신반포로 176)에 신세계백화점 입점 브랜드도 등록되어 있다. 신세계 것은 공식 목록(stores.js)이 따로 있으므로 뺀다.
- 층이 안 적힌 가게(80곳쯤)는 어느 층인지 몰라서 뺀다.
"""
import csv
import io
import json
import sys
import zipfile

from make_shinsegae import FLOORS, official_names, squash

FLOOR_IDS = {"1", "2"}  # 터미널 대합실과 파미에스테이션이 있는 층. 3층부터는 이 주소에 백화점 브랜드만 나오고, 지하 1층은 신세계 안내도로 이미 들어 있다.
NOT_SHOPS = {"과학·기술", "시설관리·임대"}  # 컨설팅, 인력 알선 같은 사무실


def pick(row, shinsegae):
    """자료 한 줄이 센트럴시티나 파미에스테이션 가게면 (층, 묶음 이름, 가게 이름), 아니면 None."""
    road, number = row["도로명"], row["건물본번지"]
    if row["법정동명"] != "반포동" or not (("신반포로" in road and number == "176") or ("사평대로" in road and number == "205")):
        return None
    name, words = " ".join(row["상호명"].split()), row["상호명"] + row["지점명"] + row["건물명"]
    if row["층정보"] not in FLOOR_IDS or row["상권업종대분류명"] in NOT_SHOPS or "신세계" in words or "백화점" in words or any(k in squash(name) for k in shinsegae):
        return None
    place = "파미에스테이션" if number == "205" or "파미에" in words else "센트럴시티"
    return row["층정보"], f"{place} {'먹을 곳' if row['상권업종대분류명'] == '음식' else '가게·서비스'}", name


def self_check():
    row = {"도로명": "서울특별시 서초구 신반포로", "건물본번지": "176", "법정동명": "반포동", "상호명": "굿모닝약국", "지점명": "", "건물명": "센트럴시티", "층정보": "1", "상권업종대분류명": "소매"}
    assert pick(row, {"알렉산더왕"}) == ("1", "센트럴시티 가게·서비스", "굿모닝약국")
    assert pick({**row, "상호명": "알렉산더왕"}, {"알렉산더왕"}) is None            # 신세계 공식 목록에 있는 이름
    assert pick({**row, "상호명": "도제신세계강남점"}, set()) is None and pick({**row, "층정보": ""}, set()) is None
    assert pick({**row, "상호명": "호호식당파미에스테이션", "상권업종대분류명": "음식"}, set()) == ("1", "파미에스테이션 먹을 곳", "호호식당파미에스테이션")
    assert pick({**row, "건물본번지": "194"}, set()) is None                          # 경부선 터미널 주소
    assert pick({**row, "상권업종대분류명": "과학·기술"}, set()) is None and pick({**row, "층정보": "B1"}, set()) is None


def main(path):
    self_check()
    shinsegae = {k for floor in FLOORS for k in official_names(floor) if len(k) >= 3}  # 두 글자 이름은 다른 가게 이름에 우연히 들어 있기 쉽다
    archive = zipfile.ZipFile(path)
    seoul = [n for n in archive.namelist() if "서울" in n]
    assert len(seoul) == 1, f"서울 파일을 못 찾음: {archive.namelist()}"
    stores = {}
    with archive.open(seoul[0]) as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline="")):
            found = row["시군구명"] == "서초구" and pick(row, shinsegae)
            if found:
                names = stores.setdefault(found[0], {}).setdefault(found[1], [])
                if found[2] not in names:
                    names.append(found[2])
    assert stores, "센트럴시티 가게를 하나도 못 찾음(자료 형식이 바뀌었을 수 있다)"
    stores = {floor: {cat: sorted(names) for cat, names in sorted(cats.items())} for floor, cats in sorted(stores.items())}
    with open("gosok/central.js", "w", encoding="utf-8") as f:
        f.write("// make_central.py가 만든 파일. 손으로 고치지 않는다.\n")
        f.write(f"// 센트럴시티와 파미에스테이션의 가게 이름과 층. 공공데이터 '소상공인시장진흥공단 상가(상권)정보'({seoul[0][-10:-4]})에서 뽑았다.\n")
        f.write("// 사업자 등록 이름이라 간판과 다를 수 있고 없어진 가게가 섞여 있을 수 있다. 실내 자리는 없다. stores.js의 목록에 층별로 보탠다.\n")
        f.write("for (const [floor, more] of Object.entries(" + json.dumps(stores, ensure_ascii=False, indent=1) + ")) Object.assign(STORES[floor] ||= {}, more);\n")
    for floor, cats in stores.items():
        print(f"{floor}층: " + ", ".join(f"{cat} {len(names)}곳" for cat, names in cats.items()))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("쓰는 법: python3 make_central.py <소상공인시장진흥공단 상가(상권)정보 zip 파일>")
    main(sys.argv[1])
