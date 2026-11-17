"""신세계백화점 강남점 층 안내도 그림에서 매장 칸과 이름을 읽어 gosok/shinsegae.shapes.tsv, shinsegae.poi.tsv를 만든다.

쓰는 법: python3 tools/make_shinsegae.py <그림 폴더>   (그다음 python3 tools/make_map.py gosok)
그림 폴더에는 신세계백화점 공식 층별 안내의 "층 안내도" 그림(2000x1500)을 층 이름으로 넣는다: 11.png, 10.png, ... 1M.png, 1.png, B1.png
B1-detail.png도 넣는다: 지하 1층 "스위트 파크" 탭의 그림(스위트 파크와 하우스오브신세계 쪽 확대도). 지하 1층 그림에서 글자가 작아 못 읽는 매장 이름을 여기서 읽는다.

맥에서만 돈다. 맥에 들어 있는 도구 두 가지를 쓴다: sips(그림 형식 바꾸기), osascript(Vision으로 글자 읽기).
하는 일:
1. 그림에서 회색으로 칠해진 덩어리(매장 칸)를 찾아 테두리를 다각형으로 딴다.
2. 칸들을 부풀렸다 줄여서 칸 사이 통로까지 메운 모양을 바닥으로 삼는다(그림에 바닥 모양이 따로 없다).
3. 글자를 읽어서 어느 칸 안에 있는지 보고, gosok/stores.js의 공식 매장 이름과 맞으면 공식 이름과 종류를 쓴다.
4. 그림 좌표를 고속터미널 실내 좌표(고투몰과 같은 틀)로 옮긴다. 아래 "자리 맞추기" 참고.
칸 모양은 운영사의 도면을 옮긴 것이다. 널리 공개하기 전에 허락을 구해야 한다.
엘리베이터, 화장실 같은 그림 기호는 읽지 않는다(글자가 아니라서).
"""
import array
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

FLOORS = ["11", "10", "9", "8", "7", "6", "5", "4", "3", "2", "1M", "1", "B1"]
GREY = range(212, 231)   # 매장 칸의 회색(밝기 221). 통로는 흰색, 글자와 벽은 검정이다. 칸 사이 가는 금(중간 밝기)에서 끊기도록 좁게 잡는다.
MIN_AREA = 250           # 이보다 작은 덩어리(px)는 얼룩으로 보고 버린다
CLOSE = 70               # 바닥을 만들 때 칸을 부풀리는 폭(px). 가장 넓은 통로나 광장 폭의 절반보다 커야 메워진다.
SIGN = re.compile(r"엘리베이터|에스컬레이터|화장실|음수대|보관소|제세동기")  # 그림 아래 기호 설명에 나오는 말
GUIDE = re.compile(r"\d+ ?GATE|지하철|고속터미널 ?[경호][부남]선|호남선 ?터미널|JW 메리어트 서울 연결통로|파미에스테이션")  # 칸 밖 글자 중 길 안내로 남길 말

# 자리 맞추기. 그림은 북쪽이 왼쪽이다(1층 그림에 경부선이 위, 호남선이 아래, 파미에스테이션이 오른쪽으로 적혀 있다).
# 실내 좌표는 고투몰과 같은 틀이다: 10cm 단위, x는 동쪽, y는 남쪽, 건물 방향으로 돌아가 있다.
# 그림의 왼쪽 날개(본관)를 OSM의 신세계백화점 건물(가로 67m, 세로 85m)에 맞췄다: 본관 길이로는 1px = 8.25cm, 폭으로는 8.8cm라 8.5cm로 잡았다.
# 지하 1층 그림은 축척이 다르다. 남북 양 끝이 위층과 같다고 보고 1px = 10.26cm로 잡았고, 그러면 서쪽 끝이 OSM의 센트럴시티 건물 서쪽 벽과 3m 안에서 맞는다.
# shortcut: 건물 테두리에 맞춘 것이라 바깥 지도와 10m쯤 어긋날 수 있다. 실측 기준점(출입구 좌표 등)이 생기면 그것으로 다시 맞춘다.
EAST, NORTH = 2589, 578  # OSM 신세계백화점 건물의 동쪽 벽 x, 북쪽 벽 y
FRAME = {"B1": (409, 293, 1.026), "1": (31, 460, 0.85), "1M": (31, 407, 0.85), "2": (31, 407, 0.85)}  # 층: (북쪽 벽이 놓인 가로 px, 동쪽 벽이 놓인 세로 px, 1px이 몇 칸인지)
DETAIL = (0.5736, 871, 187)  # B1-detail.png의 한 점 -> B1.png의 점: 곱할 값, 더할 x, 더할 y. 두 그림에서 똑같이 읽힌 글자 38개의 위치로 맞췄다(어긋남 가운데값 8px).
FRAME_UP = (31, 491, 0.85)  # 3층부터. 층마다 그림이 놓인 높이가 달라서, 에스컬레이터 기호 위치로 1층과 2층의 어긋남(-31px, -84px)을 쟀다.


def place(floor, px, py):
    """그림의 한 점을 실내 좌표로 옮긴다. 그림의 오른쪽이 남쪽, 아래쪽이 서쪽이다."""
    left, top, k = FRAME.get(floor, FRAME_UP)
    return round(EAST - (py - top) * k), round(NORTH + (px - left) * k)


OCR_JXA = """
ObjC.import('Foundation'); ObjC.import('Vision');
function run(argv) {
  const req = $.VNRecognizeTextRequest.alloc.init;
  req.recognitionLevel = 0; req.recognitionLanguages = $(['ko-KR', 'en-US']); req.usesLanguageCorrection = false; req.minimumTextHeight = 0.004;
  const handler = $.VNImageRequestHandler.alloc.initWithURLOptions($.NSURL.fileURLWithPath(argv[0]), $({}));
  if (!handler.performRequestsError($([req]), null)) return '';
  const res = req.results, out = [];
  for (let i = 0; i < res.count; i++) {
    const o = res.objectAtIndex(i), b = o.boundingBox, top = o.topCandidates(1).objectAtIndex(0);
    out.push([b.origin.x, 1 - b.origin.y - b.size.height, b.size.width, b.size.height, top.confidence, top.string.js].join('\\t'));
  }
  return out.join('\\n');
}
"""


def read_brightness(path):
    """그림을 밝기(0~255) 바이트 줄로 읽는다. (가로, 세로, 위에서부터의 밝기)"""
    with tempfile.TemporaryDirectory() as tmp:
        bmp = os.path.join(tmp, "a.bmp")
        subprocess.run(["sips", "-s", "format", "bmp", path, "--out", bmp], check=True, capture_output=True)
        raw = open(bmp, "rb").read()
    offset = int.from_bytes(raw[10:14], "little")
    w = int.from_bytes(raw[18:22], "little", signed=True)
    h = int.from_bytes(raw[22:26], "little", signed=True)
    bpp = int.from_bytes(raw[28:30], "little") // 8
    assert bpp in (3, 4), f"모르는 BMP 형식: {bpp * 8}비트"
    stride = (w * bpp + 3) // 4 * 4
    rows = [raw[offset + y * stride + 1: offset + y * stride + w * bpp: bpp] for y in range(abs(h))]  # 초록 채널 = 밝기(그림이 흑백이다)
    if h > 0:
        rows.reverse()  # BMP는 아래 줄부터 적혀 있다
    return w, abs(h), b"".join(rows)


def find_regions(w, h, mask):
    """0과 1로 된 그림에서 1인 덩어리마다 번호를 매긴다. (번호판, {번호: (넓이, 맨 윗줄 맨 왼쪽 점)})"""
    label = array.array("i", bytes(4 * w * h))
    regions = {}
    start = mask.find(1)
    while start >= 0:
        if not label[start]:
            n = len(regions) + 1
            stack, area = [start], 0
            label[start] = n
            while stack:
                p = stack.pop()
                area += 1
                x = p % w
                for q in (p - w, p + w, p - 1 if x else -1, p + 1 if x < w - 1 else -1):
                    if 0 <= q < w * h and mask[q] and not label[q]:
                        label[q] = n
                        stack.append(q)
            regions[n] = (area, start)
        start = mask.find(1, start + 1)
    return label, regions


def grow(rows, w, r):
    """비트로 적은 줄들(한 줄이 정수 하나)에서 1인 곳을 사방으로 r점 부풀린다."""
    full, n = (1 << w) - 1, 0
    while n < r:
        s = min(2 * n + 1, r - n)  # 이미 n만큼 부풀었으면 2n+1까지는 한 번에 더해도 틈이 안 생긴다
        rows = [(v | v << s | v >> s) & full for v in rows]
        rows = [v | (rows[i - s] if i >= s else 0) | (rows[i + s] if i + s < len(rows) else 0) for i, v in enumerate(rows)]
        n += s
    return rows


def close_gaps(w, h, mask, r):
    """칸들을 r만큼 부풀렸다가 다시 r만큼 줄인다. 칸 사이 통로(폭 2r 이하)가 메워진 모양이 남는다."""
    full = (1 << w) - 1
    rows = [int(mask[y * w:(y + 1) * w].translate(BITS).decode(), 2) for y in range(h)]
    rows = grow([~v & full for v in grow(rows, w, r)], w, r)
    return b"".join(format(~v & full, f"0{w}b").encode().translate(UNBITS) for v in rows)


BITS = bytes(48 + (v & 1) for v in range(256))   # 0, 1 -> 글자 '0', '1'
UNBITS = bytes(v & 1 for v in range(256))        # 글자 '0', '1' -> 0, 1


def outline(w, h, label, n, start):
    """덩어리의 바깥 테두리를 한 바퀴 돌아 점 목록으로 만든다(무어 이웃 따라가기)."""
    inside = lambda x, y: 0 <= x < w and 0 <= y < h and label[y * w + x] == n
    ring = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]  # 시계 방향 여덟 이웃
    x, y = start % w, start // w  # 가장 위 줄의 가장 왼쪽 점
    pts, d, first = [(x, y)], 7, None
    for _ in range(4 * (w + h) * 4):
        for i in range(8):
            k = (d + i) % 8
            nx, ny = x + ring[k][0], y + ring[k][1]
            if inside(nx, ny):
                break
        else:
            return pts  # 점 하나짜리
        step = (x, y, k)
        if first is None:
            first = step
        elif step == first:
            return pts[:-1]  # 마지막 점은 시작점과 같다
        x, y, d = nx, ny, (k + 7) % 8 if k % 2 == 0 else (k + 6) % 8  # 방금 바깥으로 확인한 이웃 바로 다음부터 훑는다
        pts.append((x, y))
    return pts


def simplify(ring, eps=1.6):
    """닫힌 테두리에서 거의 일직선인 점들을 덜어 낸다(더글러스-포이커)."""
    if len(ring) < 4:
        return ring
    far = max(range(len(ring)), key=lambda i: (ring[i][0] - ring[0][0]) ** 2 + (ring[i][1] - ring[0][1]) ** 2)
    out = []
    for pts in (ring[:far + 1], ring[far:] + ring[:1]):  # 시작점에서 가장 먼 점에서 둘로 잘라야 양 끝이 다른 선이 된다
        keep = {0, len(pts) - 1}
        stack = [(0, len(pts) - 1)]
        while stack:
            a, b = stack.pop()
            (x1, y1), (x2, y2) = pts[a], pts[b]
            dx, dy = x2 - x1, y2 - y1
            norm = (dx * dx + dy * dy) ** 0.5 or 1
            worst, idx = 0, -1
            for i in range(a + 1, b):
                dist = abs(dy * (pts[i][0] - x1) - dx * (pts[i][1] - y1)) / norm
                if dist > worst:
                    worst, idx = dist, i
            if worst > eps:
                keep.add(idx)
                stack += [(a, idx), (idx, b)]
        out += [pts[i] for i in sorted(keep)][:-1]
    return out


def self_check():
    """작은 그림으로 덩어리 찾기, 테두리 따기, 점 덜어 내기, 통로 메우기, 자리 옮기기를 확인한다."""
    w, h = 12, 9
    mask = bytearray(w * h)
    for y in range(2, 7):
        for x in range(3, 10):
            mask[y * w + x] = 1
    mask[4 * w + 6] = 0  # 칸 안의 글자(구멍)
    label, regions = find_regions(w, h, bytes(mask))
    assert list(regions.values()) == [(34, 2 * w + 3)], regions
    ring = outline(w, h, label, 1, 2 * w + 3)
    assert len(ring) == 20 and len(set(ring)) == 20, ring
    assert sorted(simplify(ring)) == [(3, 2), (3, 6), (9, 2), (9, 6)], simplify(ring)
    two = bytearray(w * h)  # 두 칸 사이에 2점짜리 통로
    for y in range(3, 6):
        for x in (2, 3, 4, 7, 8, 9):
            two[y * w + x] = 1
    closed = close_gaps(w, h, bytes(two), 1)
    assert closed[4 * w + 5] == closed[4 * w + 6] == 1 and sum(closed) == 3 * 8, sum(closed)  # 통로만 메워지고 바깥으로는 안 늘어난다
    assert place("5", 31, 491) == (EAST, NORTH) and place("5", 131, 491) == (EAST, NORTH + 85) and place("5", 31, 591) == (EAST - 85, NORTH)
    assert labels([(10, 10, 60, 20, 1, "르917"), (5, 22, 70, 32, .5, "(르셉템버)"), (200, 10, 250, 20, 1, "던스트")]) == [(37.5, 21.0, "르917 (르셉템버)", .5), (225.0, 15.0, "던스트", 1)]


def read_text(path):
    """그림의 글자 줄들. [(x, y, 너비, 높이, 확신(0~1), 글자)], 위치는 그림 크기를 1로 본 값이다."""
    out = subprocess.run(["osascript", "-l", "JavaScript", "-e", OCR_JXA, path], check=True, capture_output=True, text=True).stdout
    return [(*map(float, cols[:5]), cols[5].strip()) for cols in (line.split("\t") for line in out.splitlines()) if len(cols) == 6]


squash = lambda s: re.sub(r"[\s/()&·.,\-'’:]", "", s).lower()


def labels(texts):
    """한 칸 안의 글자 줄들 (x0, y0, x1, y1, 확신, 글자)을 이름표로 묶는다. 위아래로 붙어 있고 가로로 겹치는 줄은 한 이름이다.
    [(가운데 x, 가운데 y, 이름, 가장 낮은 확신)]"""
    groups = []
    for x0, y0, x1, y1, sure, text in sorted(texts, key=lambda t: t[1]):
        for g in groups:
            if min(x1, g[2]) > max(x0, g[0]) and y0 - g[3] < 0.9 * (y1 - y0):
                g[:5] = min(g[0], x0), g[1], max(g[2], x1), max(g[3], y1), min(g[4], sure)
                g[5].append(text)
                break
        else:
            groups.append([x0, y0, x1, y1, sure, [text]])
    # 세로로 쓴 이름은 글자가 한 줄에 하나씩 읽히므로 띄우지 않고 붙인다
    return [((g[0] + g[2]) / 2, (g[1] + g[3]) / 2, ("" if all(len(t) == 1 for t in g[5]) else " ").join(g[5]), g[4]) for g in groups]


def official_names(floor):
    """gosok/stores.js에서 그 층의 {줄인 이름: (공식 이름, 종류)}를 읽는다."""
    src = open("gosok/stores.js", encoding="utf-8").read().split("const STORES = ")[1].rstrip().rstrip(";")
    stores = json.loads(re.sub(r",(\s*[}\]])", r"\1", src))
    return {squash(name): (name, cat) for cat, names in stores.get(floor, {}).items() for name in names}


def match(name, official):
    """읽은 이름과 맞는 공식 (이름, 종류). 없으면 None."""
    key = squash(name)
    if key in official:
        return official[key]
    close = difflib.get_close_matches(key, official, n=1, cutoff=0.74)
    if close:
        return official[close[0]]
    starts = [k for k in official if len(key) >= 2 and len(k) >= 2 and (k.startswith(key) or key.startswith(k))]  # "닥스"와 "닥스 숙녀"처럼 한쪽이 덧붙은 이름
    return official[starts[0]] if len(starts) == 1 else None


def main(folder):
    self_check()
    shapes, pois, report = [], [], []
    for floor in FLOORS:
        path = os.path.join(folder, floor + ".png")
        w, h, light = read_brightness(path)
        label, regions = find_regions(w, h, light.translate(bytes(1 if v in GREY else 0 for v in range(256))))
        regions = {n: v for n, v in regions.items() if v[0] >= MIN_AREA}
        xy = lambda pts: " ".join("%d,%d" % place(floor, x, y) for x, y in pts)

        # 바닥: 칸 사이 통로를 메운 모양. 칸보다 먼저 적어야 밑에 깔린다.
        closed = close_gaps(w, h, bytes(map(regions.__contains__, label)), CLOSE)
        floor_label, floor_regions = find_regions(w, h, closed)
        for n, (area, start) in floor_regions.items():
            pts = simplify(outline(w, h, floor_label, n, start), 3)
            if len(pts) >= 3:
                shapes.append((floor, "바닥면", f"s{floor}-floor{n}", xy(pts)))

        inside, loose, detail = {}, [], {}
        boxes = [(x * w, y * h, (x + bw) * w, (y + bh) * h, sure, text, inside) for x, y, bw, bh, sure, text in read_text(path)]
        if floor == "B1":
            k, dx, dy = DETAIL
            boxes += [(k * x * w + dx, k * y * h + dy, k * (x + bw) * w + dx, k * (y + bh) * h + dy, sure, text, detail)
                      for x, y, bw, bh, sure, text in read_text(os.path.join(folder, "B1-detail.png"))]
        for x0, y0, x1, y1, sure, text, inside in boxes:
            # 글자 상자 둘레와 가운데가 어느 칸에 속하는지 본다(글자 자체는 검어서 칸이 아니다)
            votes = {}
            for px, py in ((x0 - 3, (y0 + y1) / 2), (x1 + 3, (y0 + y1) / 2), ((x0 + x1) / 2, y0 - 3), ((x0 + x1) / 2, y1 + 3), ((x0 + x1) / 2, (y0 + y1) / 2)):
                if 0 <= px < w and 0 <= py < h and label[int(py) * w + int(px)] in regions:
                    votes[label[int(py) * w + int(px)]] = votes.get(label[int(py) * w + int(px)], 0) + 1
            if votes:
                inside.setdefault(max(votes, key=votes.get), []).append((x0, y0, x1, y1, sure, text))
            elif inside is not detail:
                loose.append((x0, y0, x1, y1, sure, text))
        inside = boxes[0][6] | detail  # 확대도에서 이름을 읽은 칸은 그쪽을 믿는다

        official = official_names(floor)
        named = matched = 0
        for n, (area, start) in sorted(regions.items(), key=lambda r: -r[1][0]):  # 큰 칸부터 적어야 작은 칸이 위에 그려진다
            pts = simplify(outline(w, h, label, n, start))
            if len(pts) < 3:
                continue
            shape_id, got = f"s{floor}-{n}", False
            for cx, cy, name, sure in labels(inside.get(n, [])):
                hit = match(name, official)
                if not hit and (sure < 0.9 or SIGN.search(name) or not re.search(r"[가-힣A-Za-z]{2}", name)):
                    continue  # 공식 목록에 없는 이름은 또렷이 읽힌 것만 남긴다. 작은 글자를 잘못 읽은 것, 기호 설명, 기호를 글자로 읽은 것은 버린다.
                name, kind = hit or (name, "가게")
                pois.append((floor, kind, name, *map(str, place(floor, cx, cy)), shape_id))
                got, matched = True, matched + bool(hit)
            named += got
            shapes.append((floor, "가게" if got else "기타", shape_id, xy(pts)))
        if regions:
            left, top = min(s % w for _, s in regions.values()), min(s // w for _, s in regions.values())
            for cx, cy, text, _ in labels(loose):  # 칸 밖 글자: 그림 영역 안에 있는 길 안내만, 아는 말만 남긴다(화살표나 잘못 읽은 글자가 섞여서)
                guide = GUIDE.search(text)
                if guide and cx > left and cy > top - 60:
                    pois.append((floor, "안내", guide.group().replace(" GATE", "GATE"), *map(str, place(floor, cx, cy)), ""))
        report.append(f"{floor}층: 칸 {len(regions)}개, 이름 붙은 칸 {named}개, 공식 이름과 맞은 이름 {matched}개(공식 목록 {len(official)}개)")

    with open("gosok/shinsegae.shapes.tsv", "w", encoding="utf-8") as f:
        f.write("# make_shinsegae.py가 만든 파일. 손으로 고치지 말고 make_shinsegae.py를 고쳐서 다시 돌린다.\n")
        f.write("# 신세계백화점 강남점 층 안내도 그림에서 딴 바닥과 매장 칸. 좌표는 고투몰(shapes.tsv)과 같은 틀이다.\n")
        f.write("# 건물 테두리에 맞춰 얹은 것이라 바깥 지도와 10m쯤 어긋날 수 있다. 운영사의 도면이므로 널리 공개하기 전에 허락을 구해야 한다.\n")
        f.write("# 층\t종류\tid\t꼭짓점들\n")
        f.writelines("\t".join(s) + "\n" for s in shapes)
    with open("gosok/shinsegae.poi.tsv", "w", encoding="utf-8") as f:
        f.write("# make_shinsegae.py가 만든 파일. 손으로 고치지 말고 make_shinsegae.py를 고쳐서 다시 돌린다.\n")
        f.write("# 신세계백화점 강남점 층 안내도 그림에서 읽은 매장 이름과 자리. 공식 매장 목록(stores.js)과 맞는 이름은 공식 이름과 종류를 썼고,\n")
        f.write("# 안 맞는 것은 읽은 그대로 '가게'로 두었다(글자를 잘못 읽은 것이 섞여 있을 수 있다). '안내'는 칸 밖에 적힌 길 안내 글자다.\n")
        f.write("# 층\t종류\t이름\tx\ty\t자리\n")
        f.writelines("\t".join(p) + "\n" for p in pois)
    print("\n".join(report))


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("쓰는 법: python3 tools/make_shinsegae.py <층 안내도 그림 폴더>")
    main(sys.argv[1])
