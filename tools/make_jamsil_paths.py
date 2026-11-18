"""잠실의 길찾기용 통로 선 jamsil/paths.tsv를 만든다.

쓰는 법: python3 tools/make_jamsil_paths.py  (그다음 python3 tools/make_map.py jamsil)

공식 지도 자료에 통로 연결선이 비어 있어서, jamsil/shapes.tsv의 바닥에서 가게와 시설 칸을 뺀 빈 곳(통로)을
1m짜리 모눈으로 칠하고, 그 가운데 선만 남게 깎아서(Zhang-Suen 세선화) 통로 선으로 삼는다.
표준 라이브러리만 쓴다. 층마다 몇 초씩 걸린다.
"""
import math

CELL = 10       # 모눈 한 칸. 실내 좌표 10칸 = 1m
STEP = 8        # 통로 토막의 최대 길이(모눈 칸). app.js가 가장 가까운 '끝점'에서 길을 시작하므로 끝점이 촘촘해야 한다
SPUR = 4        # 이보다 짧은 막다른 잔가지(모눈 칸)는 지운다
ISLAND = 30     # 이어진 통로를 다 합쳐 이보다 짧은 외딴 조각(모눈 칸)은 버린다. 칸 사이 틈새가 통로로 잡힌 것이다
FLOOR = ("바닥면", "바닥")


def read_shapes():
    floors = {}
    for row in open("jamsil/shapes.tsv", encoding="utf-8"):
        if not row.startswith("#"):
            floor, kind, _, pts = row.rstrip("\n").split("\t")
            floors.setdefault(floor, []).append((kind in FLOOR, [tuple(map(float, p.split(","))) for p in pts.split()]))
    return floors


def paint(cells, w, x0, y0, pts, on):
    """다각형 안에 가운데가 든 모눈 칸을 넣거나(on) 뺀다."""
    edges = list(zip(pts, pts[1:] + pts[:1]))
    ys = [p[1] for p in pts]
    for row in range(int((min(ys) - y0) / CELL), int((max(ys) - y0) / CELL) + 1):
        y = y0 + (row + .5) * CELL
        xs = sorted(x1 + (y - y1) * (x2 - x1) / (y2 - y1) for (x1, y1), (x2, y2) in edges if (y1 <= y) != (y2 <= y))
        for a, b in zip(xs[::2], xs[1::2]):
            span = range(row * w + math.ceil((a - x0) / CELL - .5), row * w + math.floor((b - x0) / CELL - .5) + 1)
            (cells.update if on else cells.difference_update)(span)


def thin(cells, w):
    """덩어리를 한 칸 굵기의 가운데 선만 남게 깎는다(Zhang-Suen). 이어진 것은 끊지 않는다."""
    ring = (-w, -w + 1, 1, w + 1, w, w - 1, -1, -w - 1)  # 북쪽부터 시계 방향
    edge = {c for c in cells if any(c + o not in cells for o in ring)}
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            kill = []
            for c in edge:
                p = [c + o in cells for o in ring]
                if 2 <= sum(p) <= 6 and sum(not p[i] and p[i - 7] for i in range(8)) == 1:
                    n, e, s, west = p[0], p[2], p[4], p[6]
                    if not (e and s and (n or west)) if step == 0 else not (n and west and (e or s)):
                        kill.append(c)
            cells.difference_update(kill)
            edge.difference_update(kill)
            edge.update(c + o for c in kill for o in ring if c + o in cells)
            changed |= bool(kill)
    return cells


def links(line, w, c):
    """가운데 선에서 c와 이어진 칸. 대각선은 옆으로 돌아갈 칸이 없을 때만 잇는다(계단 모양에 세모꼴이 생기지 않게)."""
    out = [c + o for o in (-w, 1, w, -1) if c + o in line]
    return out + [c + dx + dy for dx in (-1, 1) for dy in (-w, w) if c + dx + dy in line and c + dx not in line and c + dy not in line]


def chains(line, w):
    """가운데 선을 갈림길과 끝에서 끊어, 칸이 줄줄이 이어진 가닥들로 나눈다."""
    nb = {c: links(line, w, c) for c in line}
    knots = {c for c in line if len(nb[c]) != 2}
    out, done = [], set()

    def walk(a, b):
        chain = [a, b]
        done.update(((a, b), (b, a)))
        while chain[-1] not in knots and chain[-1] != a:
            nxt = next(n for n in nb[chain[-1]] if n != chain[-2])
            done.update(((chain[-1], nxt), (nxt, chain[-1])))
            chain.append(nxt)
        return chain

    for a in knots:
        out += [walk(a, b) for b in nb[a] if (a, b) not in done]
    for a in line:  # 갈림길이 없는 고리
        if a not in knots and (a, nb[a][0]) not in done:
            out.append(walk(a, nb[a][0]))
    return out, nb


def clear(a, b, w, free):
    """a에서 b까지 곧게 갈 때 반 칸씩 짚어 본 자리가 모두 통로 칸인지."""
    n = int(math.dist(a, b) * 2) + 1
    return all(round(a[1] + (b[1] - a[1]) * t / n) * w + round(a[0] + (b[0] - a[0]) * t / n) in free for t in range(n + 1))


def straighten(chain, w, free):
    """가닥을 곧은 토막들로 줄인다. 토막은 STEP보다 길지 않고, 가닥에서 한 칸 넘게 벗어나지 않고, 통로 밖으로 나가지 않는다."""
    at = [(c % w, c // w) for c in chain]

    def ok(i, j):
        (ax, ay), (bx, by) = at[i], at[j]
        d = math.hypot(bx - ax, by - ay) or 1
        return all(abs((bx - ax) * (ay - y) - (ax - x) * (by - ay)) / d <= 1 for x, y in at[i + 1:j]) and clear(at[i], at[j], w, free)

    out, i = [], 0
    while i < len(at) - 1:
        j = next(j for j in range(min(i + STEP, len(at) - 1), i, -1) if j == i + 1 or ok(i, j))
        out.append((at[i], at[j]))
        i = j
    return out


def floor_paths(shapes):
    xs, ys = zip(*(p for _, pts in shapes for p in pts))
    x0, y0 = min(xs) - 2 * CELL, min(ys) - 2 * CELL  # 가장자리에 빈 줄을 둬서 이웃 칸 계산이 옆줄로 넘어가지 않게 한다
    w = int((max(xs) - x0) / CELL) + 3
    free = set()
    for on in (True, False):  # 바닥을 다 칠한 다음 가게와 시설 칸을 뺀다
        for is_floor, pts in shapes:
            if is_floor == on:
                paint(free, w, x0, y0, pts, on)
    line = thin(set(free), w)
    all_chains, nb = chains(line, w)
    for chain in all_chains:  # 짧은 막다른 잔가지 지우기
        if len(chain) <= SPUR and (len(nb[chain[0]]) == 1) != (len(nb[chain[-1]]) == 1):
            line.difference_update(chain[1:] if len(nb[chain[0]]) > 1 else chain[:-1])
    segs = [s for chain in chains(line, w)[0] for s in straighten(chain, w, free)]

    # 외딴 조각 버리기: 끝점이 이어진 토막끼리 묶어 길이를 더한다
    group = {}
    def find(p):
        while group.setdefault(p, p) != p:
            group[p] = p = group[group[p]]
        return p
    for a, b in segs:
        group[find(a)] = find(b)
    total = {}
    for a, b in segs:
        total[find(a)] = total.get(find(a), 0) + math.dist(a, b)
    segs = [s for s in segs if total[find(s[0])] >= ISLAND]

    # 검산: 통로 선이 벽을 뚫지 않는다
    assert all(clear(a, b, w, free) for a, b in segs), "통로 선이 칸을 지나감"
    center = lambda x, y: (round(x0 + (x + .5) * CELL), round(y0 + (y + .5) * CELL))
    return [(*center(*a), *center(*b)) for a, b in segs], len({find(s[0]) for s in segs})


def main():
    with open("jamsil/paths.tsv", "w", encoding="utf-8") as f:
        f.write("# make_jamsil_paths.py가 만든 파일. 잠실의 길찾기용 통로 선(토막마다 양 끝점). 좌표계는 poi.tsv와 같다.\n")
        f.write("# 공식 자료에 통로 선이 없어서, shapes.tsv의 바닥에서 가게와 시설 칸을 뺀 빈 곳의 가운데를 따라 만들어 낸 것이다.\n")
        f.write("# 층\tx1\ty1\tx2\ty2\n")
        for floor, shapes in read_shapes().items():
            segs, groups = floor_paths(shapes)
            f.writelines(f"{floor}\t" + "\t".join(map(str, s)) + "\n" for s in segs)
            print(f"{floor}: 통로 토막 {len(segs)}개, 이어진 덩어리 {groups}개")


if __name__ == "__main__":
    main()
