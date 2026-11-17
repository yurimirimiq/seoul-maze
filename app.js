// 날짜가 YYYY-MM-DD 글자라서 글자 비교만으로 앞뒤를 가릴 수 있다.
const isOpen = (e, today) => e.start <= today && today <= e.end;
// 'Hall C (3층)' -> ['Hall C', '3'], 층이 안 적힌 곳은 ['로비']
const splitFloor = place => { const m = place.match(/\s*\(?(\d)층\)?/); return m ? [place.replace(m[0], '').trim(), m[1]] : [place]; };
// 두 네모가 겹치는지. 이름표가 서로 겹치지 않게 고를 때 쓴다.
const overlaps = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const t = { start: '2026-01-01', end: '2026-01-31' };
console.assert(isOpen(t, '2026-01-01') && isOpen(t, '2026-01-31') && !isOpen(t, '2025-12-31') && !isOpen(t, '2026-02-01'), 'isOpen 자가 점검 실패');
console.assert(splitFloor('Hall C, D (3층)').join() === 'Hall C, D,3' && splitFloor('컨퍼런스룸(남) 4층').join() === '컨퍼런스룸(남),4' && splitFloor('로비').join() === '로비', 'splitFloor 자가 점검 실패');
console.assert(overlaps({ x: 0, y: 0, w: 10, h: 10 }, { x: 9, y: 9, w: 5, h: 5 }) && !overlaps({ x: 0, y: 0, w: 10, h: 10 }, { x: 10, y: 0, w: 5, h: 5 }), 'overlaps 자가 점검 실패');

// 가게 종류 -> 칸 색. 종류 이름은 장소마다 달라서(패션의류, 롯데백화점 쇼핑 ...) 들어 있는 낱말로 고른다.
// 앞에 있을수록 약도에서 이름표가 먼저 나온다. 어디에도 안 맞으면 시설 색(회색)이다.
const TINTS = [
  [/엔터|문화|갤러리|서점|취미/, '#7c5cd6'], [/라이프|리빙/, '#2f9a6a'],
  [/잡화|액세서리|ACC|소품|핸드백|구두|슈즈|주얼리|러기지|타이/, '#5a66cf'],
  [/패션|의류|쇼핑|캐주얼|컨템포러리|클래식|뷰틱|RTW|디자이너|골프|스포츠|란제리|모피|커리어|엘레강스|트래디셔널|퍼니싱/, '#3d7fd0'],
  [/레스토랑|카페|먹을|식당|푸드|델리|스위트|그로서리|수산|축산|청과|채소|양곡|조리|음료|주류|냉동/, '#ef8a2b'],
  [/뷰티|화장품/, '#dc5a9a'], [/홈|가전|키친|테이블|디지털/, '#9a7440'], [/키즈|아동|신생아|완구|캐릭터/, '#d9a514'],
  [/서비스|편의|휴게|상품권|건강|전체|테넌트/, '#5b6b85'], [/가게/, '#8f86c4'],
];
const rank = kind => { const i = TINTS.findIndex(([re]) => re.test(kind)); return i < 0 ? TINTS.length : i; };
const tint = kind => TINTS[rank(kind)]?.[1] || '#9aa3b5';
const minor = s => s.kind === '편의시설' || s.kind === '안내'; // 가게가 아닌 것. 이름을 흐리게 쓴다.

// 약도 그리기: 길 -> 건물 -> 실내(층별) -> 늘 보이는 이름과 표지판 순서로 쌓는다
const svg = document.getElementById('map');
const el = (tag, attrs, text, parent = svg) => {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text) n.textContent = text;
  return parent.appendChild(n);
};
svg.setAttribute('viewBox', `0 0 ${MAP.width} ${MAP.height}`);
for (const r of MAP.roads) el('polyline', { points: r.pts, 'stroke-width': r.w, class: r.big ? 'road big' : 'road' });
for (const pts of MAP.blocks) el('polygon', { points: pts, class: 'block' });
for (const b of MAP.buildings) el('polygon', { points: b.pts });
const indoor = el('g'); // 층별 실내 그림이 들어갈 자리
for (const n of MAP.roadNames) el('text', { x: n.x, y: n.y, class: 'roadname', transform: `rotate(${n.rot} ${n.x} ${n.y})` }, n.name);

// 가게와 편의시설을 층별로 나눠 둔다. 그림은 그 층을 처음 볼 때 그린다(잠실처럼 칸이 수천 개인 곳이 있어서).
const byFloor = {};
for (const s of MAP.spots) if (s.floor) (byFloor[s.floor] ||= []).push(s);
for (const list of Object.values(byFloor)) list.sort((a, b) => rank(a.kind) - rank(b.kind));
const drawFloor = id => {
  const g = el('g', {}, '', indoor);
  const list = MAP.shapes[id] || [];
  // 바닥 모양이 자료에 없는 곳(코엑스)은 모든 칸을 굵은 흰 테두리로 한 번 깔아 통로까지 하얗게 메운다
  if (list.length && !list.some(([kind]) => kind === '바닥면')) {
    el('path', { d: list.map(([, pts]) => 'M' + pts.replaceAll(' ', 'L') + 'Z').join(''), class: 'halo' }, '', g);
  }
  // 칸은 가게 종류 색을 옅게 칠한다(--tint). 화장실 같은 시설 칸은 회색이다.
  const rooms = el('g', { class: 'rooms' }, '', g);
  for (const [kind, pts] of list) {
    const cls = { '바닥면': 'ground', '빈곳': 'void', '바닥': 'wall', '기타': 'etc' }[kind];
    const room = el('polygon', cls ? { points: pts, class: cls } : { points: pts }, '', rooms);
    if (!cls) room.style.setProperty('--tint', tint(kind));
  }
  for (const s of byFloor[id] || []) {
    s.room = rooms.children[s.shape]; // 이 가게가 차지한 칸. 칸이 없는 곳만 점으로 찍는다.
    if (!s.room) s.dot = el('circle', { cx: s.x, cy: s.y, r: .7, fill: tint(s.kind), class: 'spot' }, '', g);
  }
  for (const s of byFloor[id] || []) {
    s.label = el('text', { x: s.x, y: s.y, dx: s.room ? 0 : '.8em', class: 'spotname' + (s.room ? ' mid' : '') + (minor(s) ? ' minor' : '') }, s.name, g);
  }
  return g;
};

const signs = []; // 늘 보이는 것들이 차지한 자리. 가게 이름표가 이 위에 겹치지 않게 한다.
for (const b of MAP.buildings) { el('text', { x: b.x, y: b.y, class: 'bname' }, b.name); signs.push({ x: b.x, y: b.y, name: b.name }); }
const stations = new Set(); // 역 이름은 출구가 여럿이어도 한 번만 쓴다
for (const s of MAP.spots.filter(s => !s.floor)) {
  const exit = s.name.match(/^(.+역) (.+)번 출구$/);
  if (!exit || !s.line) { el('text', { x: s.x, y: s.y, class: 'bname' }, s.name); signs.push(s); continue; }
  // 지하철 출구는 실제 표지판처럼 그린다: 노선 색 동그라미 + 노란 출구 번호
  const line = s.line;
  const below = s.y > MAP.height / 2; // 이름이 건물과 겹치지 않게 남쪽 절반은 아래에, 북쪽 절반은 위에 쓴다
  const w = 2 + exit[2].length * 1.7;
  const left = s.x - (4.6 + w) / 2;
  const g = el('g', { class: 'keep' }); // 표지판은 약도를 키워도 같은 크기로 남는다
  el('circle', { cx: left + 2, cy: s.y, r: 2, class: 'line l' + line }, '', g);
  el('text', { x: left + 2, y: s.y + 1, class: 'sign l' + line }, line, g);
  el('rect', { x: left + 4.6, y: s.y - 2, width: w, height: 4, rx: .6, class: 'exit' }, '', g);
  el('text', { x: left + 4.6 + w / 2, y: s.y + 1, class: 'sign' }, exit[2], g);
  if (!stations.has(exit[1])) el('text', { x: s.x, y: below ? s.y + 5.6 : s.y - 3.2, class: 'fixed' }, exit[1], g);
  stations.add(exit[1]);
  signs.push({ x: s.x, y: s.y, name: exit[1] + '  ' });
}
const ping = el('circle', { id: 'ping', r: 2.4, display: 'none' });
const pin = el('circle', { id: 'pin', r: 2.4, class: 'keep', display: 'none' });
// 길 안내: 길(파란 선), GPS 오차 범위(옅은 원), 출발지(파란 점)
const routeLine = el('polyline', { id: 'route', display: 'none' });
const meRing = el('circle', { id: 'mering', display: 'none' });
const me = el('circle', { id: 'me', r: 1.6, class: 'keep', display: 'none' });

// 이름으로 찾기. 건물은 이름, 가게는 '층/이름'. 화장실처럼 같은 이름이 여러 곳이면 다 담긴다.
const places = {};
for (const b of MAP.buildings) places[b.name] = [b];
for (const s of MAP.spots) if (s.floor) (places[s.floor + '/' + s.name] ||= []).push(s);

const add = (parent, tag, text, cls) => {
  const n = parent.appendChild(document.createElement(tag));
  if (text) n.textContent = text;
  if (cls) n.className = cls;
  return n;
};

// 약도 키우기와 줄이기. 손가락으로 끌면 옮겨진다.
const scroller = document.getElementById('mapscroll');
const [zoomIn, zoomOut] = document.querySelectorAll('.zoom button');
// 약도가 볼 자리를 빈틈없이 덮는 가장 작은 크기. 이보다 줄이면 약도 밖 빈 띠가 보여서 여기까지만 줄인다.
const fit = () => Math.max(1, scroller.clientHeight / scroller.clientWidth * MAP.width / MAP.height);
const MAX_ZOOM = 32; // 지하상가 칸은 4m 남짓이라 이만큼 키워야 번호가 다 보인다
let zoom = 1, floor, picked = [];
let live = null, settle; // live: 손가락이나 휠로 늘리는 중인 크기 {z, at}. settle: 멈추면 반영하는 타이머

// 지금 층의 가게 이름표 가운데 서로 겹치지 않는 것만 보여 준다. 키울수록 더 많이 보인다.
const relabel = () => {
  const px = svg.clientWidth / MAP.width; // 약도 1칸이 화면에서 몇 px인지
  const font = 11;                        // style.css의 약도 글자 크기(px)와 같아야 한다
  svg.style.setProperty('--u', 1 / px);   // 글자, 점, 표지판을 약도 크기와 상관없이 화면에서 같은 크기로 그리게 한다
  const width = name => [...name].reduce((w, ch) => w + (ch.charCodeAt(0) < 128 ? .6 : 1), 0) * font;
  const kept = signs.map(g => ({ x: g.x * px - width(g.name) / 2, y: g.y * px - font * .7, w: width(g.name), h: font * 1.4 }));
  // 편의시설(계단, 화장실 ...)은 가게 이름과 섞이면 어지러워서 4배 넘게 키웠을 때만 이름이 나온다.
  // 칸이 없어 점으로만 찍히는 편의시설은 목록에서 골랐을 때만 보인다.
  const here = byFloor[floor] || [];
  const shown = s => picked.includes(s) || (s.kind !== '편의시설' ? true : s.room && zoom >= 4);
  for (const s of here) {
    s.label.style.display = 'none';
    if (s.dot) s.dot.style.display = s.kind !== '편의시설' || picked.includes(s) ? '' : 'none';
  }
  for (const s of [...picked.filter(s => s.floor === floor), ...here.filter(s => shown(s) && !picked.includes(s))]) {
    // 이름이 차지할 자리에 숨 쉴 틈을 조금 둔다. 칸이 있는 가게는 가운데 정렬, 점만 있는 곳은 점 오른쪽.
    const w = width(s.name) + font * (s.room ? .4 : 1.4);
    const box = { x: s.x * px - (s.room ? w / 2 : 0), y: s.y * px - font * .65, w, h: font * 1.3 };
    // 끝까지 키웠을 때는 겹치더라도 이름을 다 보여 준다. 같은 이름끼리 겹친 것(위아래 에스컬레이터 쌍)만 하나로 둔다.
    const hit = kept.find(k => overlaps(k, box));
    const show = picked.includes(s) || !hit || (zoom === MAX_ZOOM && hit.name !== s.name);
    s.label.style.display = show ? '' : 'none';
    if (show) kept.push({ ...box, name: s.name });
  }
};
// at: 그 자리가 움직이지 않게 키울 화면 위치(스크롤 상자 기준). 안 주면 가운데.
const setZoom = (z, at = { x: scroller.clientWidth / 2, y: scroller.clientHeight / 2 }) => {
  clearTimeout(settle); live = null; svg.style.transform = svg.style.willChange = ''; // 늘려만 둔 것(zoomLive)이 있으면 지우고 제대로 그린다
  const mx = (scroller.scrollLeft + at.x) / zoom, my = (scroller.scrollTop + at.y) / zoom;
  zoom = Math.min(MAX_ZOOM, Math.max(fit(), z));
  svg.style.width = zoom * 100 + '%';
  scroller.scrollTo(mx * zoom - at.x, my * zoom - at.y);
  zoomIn.disabled = zoom === MAX_ZOOM;
  zoomOut.disabled = zoom === fit();
  relabel();
};
zoomIn.onclick = () => setZoom(zoom * 2);
zoomOut.onclick = () => setZoom(zoom / 2);
// 휠이나 손가락으로 키우는 동안에는 약도를 다시 그리지 않고 그림째 늘려만 둔다. 다시 그리기(칸 크기 바꾸기, 이름표 고르기)는 무거워서
// 움직일 때마다 하면 폰에서 뚝뚝 끊긴다. 손을 떼거나 잠깐 멈추면 그때 한 번만 제대로 다시 그린다(setZoom).
const zoomLive = (z, at) => {
  if (!live) { // 늘리는 중심은 처음 잡은 자리로 둔다
    svg.style.transformOrigin = `${scroller.scrollLeft + at.x}px ${scroller.scrollTop + at.y}px`;
    svg.style.willChange = 'transform';
    live = { at };
  }
  live.z = Math.min(MAX_ZOOM, Math.max(fit(), z));
  svg.style.transform = `scale(${live.z / zoom})`;
  clearTimeout(settle);
  settle = setTimeout(commit, 200);
};
const commit = () => live && setZoom(live.z, live.at);
// 마우스 휠이나 트랙패드로도 키우고 줄인다. 커서가 있는 자리를 중심으로 움직인다.
scroller.addEventListener('wheel', e => {
  const from = live ? live.z : zoom;
  const next = Math.min(MAX_ZOOM, Math.max(fit(), from * Math.exp(-e.deltaY * (e.ctrlKey ? .01 : .002)))); // ctrlKey = 트랙패드 두 손가락 벌리기
  if (next === from) return; // 더 줄일 수 없으면 페이지가 평소처럼 스크롤되게 둔다
  e.preventDefault();
  const box = scroller.getBoundingClientRect();
  zoomLive(next, { x: e.clientX - box.left, y: e.clientY - box.top });
}, { passive: false });
// 폰에서는 두 손가락을 벌리거나 오므려서 키우고 줄인다. 처음 두 손가락을 댄 자리의 가운데를 중심으로 움직인다.
let pinch;
const spread = e => Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
scroller.addEventListener('touchstart', e => {
  commit(); // 앞서 늘려 둔 것이 있으면 먼저 반영하고 시작한다
  const box = scroller.getBoundingClientRect();
  pinch = e.touches.length !== 2 ? null : { spread: spread(e), zoom,
    at: { x: (e.touches[0].clientX + e.touches[1].clientX) / 2 - box.left, y: (e.touches[0].clientY + e.touches[1].clientY) / 2 - box.top } };
});
scroller.addEventListener('touchmove', e => {
  if (!pinch || e.touches.length !== 2) return;
  e.preventDefault(); // 페이지 전체가 커지는 것을 막는다
  zoomLive(pinch.zoom * spread(e) / pinch.spread, pinch.at);
}, { passive: false });
scroller.addEventListener('touchend', () => { pinch = null; commit(); });
// 마우스로는 끌어서 옮긴다. 손가락 하나로 끄는 것은 브라우저가 알아서 옮겨 준다.
scroller.addEventListener('pointerdown', e => {
  if (e.pointerType !== 'mouse') return;
  const move = m => scroller.scrollBy(-m.movementX, -m.movementY);
  scroller.addEventListener('pointermove', move);
  addEventListener('pointerup', () => scroller.removeEventListener('pointermove', move), { once: true });
});

// 고른 곳을 약도에 빨갛게 표시한다. 한 곳이면 그쪽으로 옮긴다. 칸이 있는 가게는 칸을 칠하고, 칸이 없는 곳은 빨간 점을 찍는다.
// 행사와 가게 목록이 같이 쓴다.
const pick = (btn, key) => {
  const to = places[key]?.[0].floor;
  if (to && to !== floor) setFloor(to); // 다른 층에 있는 곳을 고르면 그 층으로 먼저 바꾼다
  document.querySelectorAll('.pick').forEach(b => b.setAttribute('aria-pressed', b === btn));
  for (const s of picked) for (const n of [s.room, s.dot, s.label]) n?.classList.remove('on');
  picked = places[key] || [];
  if (key && !picked.length) console.error('약도에 없는 곳:', key);
  for (const s of picked) for (const n of [s.room, s.dot, s.label]) n?.classList.add('on');
  const one = picked.length === 1 && picked[0];
  for (const c of [pin, ping]) c.setAttribute('display', one && !one.room ? '' : 'none');
  if (one) {
    const y = one.pts ? one.y + 5 : one.y; // 건물은 가운데 이름을 가리지 않게 조금 아래에 찍는다
    for (const c of [pin, ping]) { c.setAttribute('cx', one.x); c.setAttribute('cy', y); }
    ping.classList.remove('go');
    ping.getBBox(); // 애니메이션을 처음부터 다시 돌리려면 한 번 읽어 줘야 한다
    ping.classList.add('go');
    scroller.scrollTo(one.x / MAP.width * svg.clientWidth - scroller.clientWidth / 2, y / MAP.height * svg.clientHeight - scroller.clientHeight / 2);
  }
  relabel();
  if (btn) scroller.scrollIntoView({ block: 'nearest' }); // 목록에서 골랐을 때만 약도가 보이게 올린다
};

// 층 고르기
const floorBtns = document.getElementById('floors');
const panel = document.getElementById('floor');
const layers = {}; // 층 id -> 그 층 실내 그림
let afterFloor = () => {}; // 층이 바뀐 뒤 할 일(길 안내가 채운다)
const setFloor = id => {
  const f = FLOORS.find(f => f.id === id);
  if (!f) return;
  floor = id;
  for (const b of floorBtns.children) {
    b.setAttribute('aria-pressed', b.dataset.floor === id);
    // 층이 많아 버튼 목록이 넘치면 고른 층이 보이게 목록만 옮긴다
    if (b.dataset.floor === id) floorBtns.scrollTop = b.offsetTop - (floorBtns.clientHeight - b.offsetHeight) / 2;
  }
  layers[id] ||= drawFloor(id);
  for (const f in layers) layers[f].style.display = f === id ? '' : 'none';
  pick(null, ''); // 다른 층에서 고른 표시를 지운다
  afterFloor();

  panel.replaceChildren();
  add(add(panel, 'h2', f.name), 'small', f.note);
  const rows = add(panel, 'ul', '', 'rows');
  for (const g of f.groups) {
    const li = add(rows, 'li');
    add(li, 'span', g.title, 'kind');
    const box = add(li, 'div');
    for (const [name, where] of g.items) add(add(box, 'p', name), 'small', where);
  }
  // 가게: 종류별로 접어 두고 하나씩 펼친다. 이름을 누르면 약도에 표시된다.
  const cats = Object.entries(STORES[id] || {});
  const total = cats.reduce((n, [, names]) => n + names.length, 0);
  const amenities = [...new Set((byFloor[id] || []).filter(s => s.kind === '편의시설').map(s => s.name))];
  if (amenities.length) cats.push(['편의시설', amenities]);
  if (!cats.length) return;
  add(panel, 'h3', total ? `가게 ${total}곳` : '편의시설');
  for (const [i, [cat, names]] of cats.entries()) {
    const box = add(panel, 'details');
    box.setAttribute('name', 'cat'); // 같은 name끼리는 하나만 펼쳐진다
    box.open = i === 0;
    const head = add(box, 'summary');
    add(head, 'i').style.background = tint(cat);
    head.append(cat);
    add(head, 'small', names.length);
    const list = add(box, 'ul', '', 'cols');
    for (const name of names) {
      const li = add(list, 'li');
      const key = id + '/' + name;
      if (!places[key]) { li.textContent = name; continue; } // 위치를 모르는 가게는 글자로만
      const btn = add(li, 'button', name, 'pick');
      if (places[key].length > 1) add(btn, 'small', ` ${places[key].length}곳`);
      btn.setAttribute('aria-pressed', 'false');
      btn.onclick = () => pick(btn, key);
    }
  }
};
for (const f of FLOORS) {
  const b = add(floorBtns, 'button', f.id);
  b.dataset.floor = f.id;
  b.setAttribute('aria-label', f.name);
  b.onclick = () => setFloor(f.id);
}
setFloor((FLOORS.find(f => f.start) || FLOORS[0]).id);
setZoom(0); // 볼 자리를 덮는 크기로 시작해서 약도 가운데를 보여 준다
scroller.scrollTo((svg.clientWidth - scroller.clientWidth) / 2, (svg.clientHeight - scroller.clientHeight) / 2);
addEventListener('resize', () => setZoom(zoom)); // 화면 크기가 바뀌면 덮는 크기도 바뀐다

// 행사 목록. 행사 자료(EVENTS)가 없는 장소는 건너뛴다.
const today = new Date().toLocaleDateString('sv'); // 'sv' 형식 = 내 시간대 기준 YYYY-MM-DD
const day = d => d.slice(5).replace('-', '.');
const fill = (id, events, emptyText, dateText) => {
  const list = document.getElementById(id);
  if (!list) return;
  if (!events.length) add(list, 'li', emptyText);
  for (const e of events) {
    const li = add(list, 'li');
    const btn = add(li, 'button', '', 'pick');
    btn.setAttribute('aria-pressed', 'false');
    const [big, small] = dateText(e);
    const date = add(btn, 'span', '', 'date');
    add(date, 'b', big);
    add(date, 'small', small);
    const [place, where] = splitFloor(e.place);
    const what = add(btn, 'span', '', 'what');
    add(what, 'b', e.name);
    add(add(what, 'small'), 'span', place).after(e.cat);
    if (where) add(btn, 'span', where + '층', 'floor');
    btn.onclick = () => {
      if (where) setFloor(where); // 행사가 열리는 층으로 같이 바꾼다
      pick(btn, e.at || MAP.main);
    };
    if (e.url) add(li, 'a', '공식 안내 보기').href = e.url;
  }
};
const byStart = (a, b) => a.start.localeCompare(b.start);
const EVENT_LIST = typeof EVENTS === 'undefined' ? [] : EVENTS;
fill('now', EVENT_LIST.filter(e => isOpen(e, today)).sort(byStart), '지금 열리는 행사가 없어요.',
  e => e.end === today ? ['오늘', '까지'] : [day(e.end), '까지']);
fill('soon', EVENT_LIST.filter(e => e.start > today).sort(byStart), '예정된 행사가 없어요.',
  e => [day(e.start), e.end === e.start ? '하루만' : '~ ' + day(e.end)]);

// ---- 찾기와 길 안내 ----
// 통로 그래프의 한 점에서 모든 점까지 가장 짧은 거리(다익스트라). nb[i] = [[이웃, 거리], ...]
// 점이 천 개 안쪽이라 가장 가까운 점을 그냥 훑어서 찾는다.
const reach = (nb, from) => {
  const dist = nb.map(() => Infinity), prev = nb.map(() => -1), done = nb.map(() => false);
  dist[from] = 0;
  for (;;) {
    let u = -1;
    for (let i = 0; i < nb.length; i++) if (!done[i] && dist[i] < Infinity && (u < 0 || dist[i] < dist[u])) u = i;
    if (u < 0) return { dist, prev };
    done[u] = true;
    for (const [v, d] of nb[u]) if (dist[u] + d < dist[v]) { dist[v] = dist[u] + d; prev[v] = u; }
  }
};
{ // 자가 점검: 0-1-2로 돌아가는 길(2)이 0-2 직통(5)보다 짧다. 3은 못 간다.
  const r = reach([[[1, 1], [2, 5]], [[0, 1], [2, 1]], [[0, 5], [1, 1]], []], 0);
  console.assert(r.dist[2] === 2 && r.prev[2] === 1 && r.dist[3] === Infinity, 'reach 자가 점검 실패');
}

const finder = document.getElementById('finder');
if (finder) {
  const [toInput, fromInput] = finder.querySelectorAll('input');
  const gps = finder.querySelector('button'), hits = document.getElementById('hits'), guide = document.getElementById('guide');
  const box = finder.parentNode; // 돋보기를 누르면 열리는 상자. 열면 바로 적을 수 있게 하고, 고르고 나면 약도가 보이게 닫는다.
  box.ontoggle = () => box.open && toInput.focus();
  box.onkeydown = e => { if (e.key === 'Escape') box.open = false; };
  const squash = s => s.toLowerCase().replace(/\s/g, '');

  // 찾을 수 있는 것 전부: 층별 가게 목록의 이름 + 약도에 자리가 있는 것(시설, 칸 번호, 안내 표시) + 층 안내에 적은 시설(전시홀 등)
  const things = [];
  for (const f of FLOORS) {
    const seen = new Set();
    const put = (name, cat) => { if (!seen.has(name)) { seen.add(name); things.push({ name, cat, floor: f, key: f.id + '/' + name, squashed: squash(name) }); } };
    for (const [cat, names] of Object.entries(STORES[f.id] || {})) for (const name of names) put(name, cat);
    for (const s of byFloor[f.id] || []) put(s.name, s.kind);
    for (const g of f.groups) if (!g.info) for (const [name] of g.items) put(name, g.title); // info: 설명만 적은 묶음은 뺀다
  }
  // 이름 앞쪽에서 맞는 것, 지금 보고 있는 층의 것을 먼저 보여 준다
  const find = q => {
    const k = squash(q);
    return !k ? [] : things.filter(t => t.squashed.includes(k))
      .sort((a, b) => a.squashed.indexOf(k) - b.squashed.indexOf(k) || (b.floor.id === floor) - (a.floor.id === floor) || a.name.localeCompare(b.name, 'ko'))
      .slice(0, 30);
  };

  // 층의 통로 그래프: 토막의 끝점을 점으로, 토막을 이웃으로 만든다. 통로 자료가 없는 층은 null.
  const graphs = {};
  const graphOf = id => {
    if (id in graphs) return graphs[id];
    const segs = (MAP.walk || {})[id];
    if (!segs) return graphs[id] = null;
    const nodes = [], nb = [], ids = new Map();
    const node = (x, y) => { const k = x + ',' + y; if (!ids.has(k)) { ids.set(k, nodes.length); nodes.push({ x, y }); nb.push([]); } return ids.get(k); };
    for (const [x1, y1, x2, y2] of segs) { const a = node(x1, y1), b = node(x2, y2), d = Math.hypot(x2 - x1, y2 - y1); nb[a].push([b, d]); nb[b].push([a, d]); }
    return graphs[id] = { nodes, nb };
  };
  const gap = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const nearest = (g, p) => g.nodes.reduce((best, n, i) => gap(n, p) < gap(g.nodes[best], p) ? i : best, 0);
  // 출발 점들에서 도착 점들까지 가장 짧은 길. 통로 자료가 있으면 통로를 따라가고, 없으면 직선이다.
  const routeOn = (id, froms, tos) => {
    const g = graphOf(id);
    let best = null;
    for (const a of froms) {
      const near = g && nearest(g, a), all = g && reach(g.nb, near);
      for (const b of tos) {
        let pts = [a, b], len = gap(a, b), along = false;
        const t = g && nearest(g, b);
        // 통로까지 걸어가는 거리가 직선 거리보다 길면 통로가 없는 곳끼리라는 뜻이라 직선으로 둔다(고속터미널 지하 1층은 통로 자료가 지하상가에만 있다)
        if (g && all.dist[t] < Infinity && gap(a, g.nodes[near]) + gap(g.nodes[t], b) < len) {
          const mid = [];
          for (let u = t; u >= 0; u = all.prev[u]) mid.unshift(g.nodes[u]);
          pts = [a, ...mid, b]; len = gap(a, g.nodes[near]) + all.dist[t] + gap(g.nodes[t], b); along = true;
        }
        if (!best || len < best.len) best = { pts, len, along, a, b };
      }
    }
    return best;
  };
  const compass = (a, b) => ['동', '남동', '남', '남서', '서', '북서', '북', '북동'][(Math.round(Math.atan2(b.y - a.y, b.x - a.x) / (Math.PI / 4)) + 8) % 8] + '쪽';
  const meters = len => { const m = Math.round(len * MAP.unit / 10) * 10; return m < 10 ? '바로 근처' : `약 ${m}m`; };
  const center = (pts, minZoom) => { // 점들이 다 보이게 키우고 가운데로 옮긴다
    const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
    const w = Math.max(...xs) - Math.min(...xs), h = Math.max(...ys) - Math.min(...ys);
    const least = MAP.width / 12; // 한 점만 볼 때도 주변이 보이게, 너무 바짝 키우지 않는다
    setZoom(Math.max(minZoom, Math.min(MAX_ZOOM, .7 * Math.min(MAP.width / Math.max(w, least), MAP.height / Math.max(h, least)))));
    scroller.scrollTo((Math.min(...xs) + w / 2) / MAP.width * svg.clientWidth - scroller.clientWidth / 2,
      (Math.min(...ys) + h / 2) / MAP.height * svg.clientHeight - scroller.clientHeight / 2);
  };

  let dest = null, start = null; // 고른 도착지와 출발지. 출발지는 GPS 위치({x, y, gps})일 수도 있다.
  let routeFloor = null;         // 길과 출발 점을 그려 둔 층
  afterFloor = () => { for (const n of [routeLine, me, meRing]) n.setAttribute('display', floor === routeFloor ? '' : 'none'); };
  const go = () => {
    routeFloor = null;
    routeLine.removeAttribute('points');
    for (const n of [me, meRing]) n.setAttribute('cx', -99);
    if (!dest) {
      if (start?.gps) { // 도착지 없이 내 위치만 본다
        routeFloor = floor;
        for (const n of [me, meRing]) { n.setAttribute('cx', start.x); n.setAttribute('cy', start.y); }
        meRing.setAttribute('r', start.gps / MAP.unit);
        afterFloor();
        center([start], 4);
      }
      guide.textContent = start ? `출발지: ${start.name}${start.gps ? ` (오차 약 ${start.gps}m)` : ''}. 도착지를 찾아 고르면 길을 알려 줘요.` : '';
      return;
    }
    setFloor(dest.floor.id);
    const tos = places[dest.key] || [];
    if (!tos.length) { guide.textContent = `${dest.name}: ${dest.floor.name}. 약도에 자리 정보는 없어요.`; return; }
    pick(null, dest.key);
    const froms = !start ? [] : start.gps ? [start] : places[start.key] || [];
    if (!froms.length) {
      guide.textContent = `${dest.name}: ${dest.floor.name}${tos.length > 1 ? `에 ${tos.length}곳` : ''}.` + (start ? ' 출발지는 약도에 자리 정보가 없어서 길은 못 그려요.' : ' 출발지를 고르면 길을 알려 줘요.');
      center(tos, 4);
      return;
    }
    if (!start.gps && start.floor.id !== dest.floor.id) {
      guide.textContent = `출발지는 ${start.floor.name}, 도착지는 ${dest.floor.name}이에요. 에스컬레이터나 엘리베이터로 ${dest.floor.name}까지 간 다음 약도의 빨간 곳을 찾아가세요.`;
      center(tos, 4);
      return;
    }
    const r = routeOn(dest.floor.id, froms, tos);
    routeFloor = dest.floor.id;
    routeLine.setAttribute('points', r.pts.map(p => p.x + ',' + p.y).join(' '));
    for (const n of [me, meRing]) { n.setAttribute('cx', r.a.x); n.setAttribute('cy', r.a.y); }
    meRing.setAttribute('r', start.gps ? start.gps / MAP.unit : 0);
    afterFloor();
    center(r.pts, 2);
    guide.textContent = `${start.name}에서 ${dest.name}까지 ${r.along ? '통로를 따라' : '직선으로'} ${meters(r.len)}`
      + (MAP.geo ? `, ${compass(r.a, r.b)}이에요.` : '예요.')
      + (start.gps ? ` GPS 위치는 실내에서 ${start.gps}m쯤 틀릴 수 있고, 지금 보는 층에 있다고 보고 계산했어요.` : '');
  };

  // 검색창에 글자를 치면 후보를 보여 주고, 후보를 고르면 onPick에 넘긴다
  const suggest = (input, onPick) => {
    hits.replaceChildren();
    if (!input.value.trim()) return onPick(null);
    for (const t of find(input.value)) {
      const btn = add(add(hits, 'li'), 'button');
      btn.type = 'button';
      add(btn, 'b', t.name);
      add(btn, 'small', t.floor.name);
      add(btn, 'small', places[t.key] ? t.cat : t.cat + ', 자리 정보 없음');
      btn.onclick = () => { input.value = t.name; hits.replaceChildren(); box.open = false; onPick(t); };
    }
    if (!hits.children.length) add(hits, 'li', '찾는 곳이 없어요. 다른 이름으로 찾아보세요.');
  };
  toInput.oninput = () => suggest(toInput, t => { dest = t; go(); });
  fromInput.oninput = () => suggest(fromInput, t => { start = t; go(); });
  finder.onsubmit = e => e.preventDefault();

  // GPS는 바깥 지도가 있는 장소에서만 쓴다. 실내와 지하에서는 잘 안 잡혀서, 안 되면 직접 고르라고 알려 준다.
  gps.hidden = !MAP.geo || !navigator.geolocation;
  gps.onclick = () => {
    guide.textContent = '위치를 찾는 중이에요…';
    navigator.geolocation.getCurrentPosition(pos => {
      const [south, north, west, east] = MAP.geo, c = pos.coords;
      const p = { name: '내 위치', gps: Math.round(c.accuracy), x: (c.longitude - west) / (east - west) * MAP.width, y: (north - c.latitude) / (north - south) * MAP.height };
      if (p.x < 0 || p.x > MAP.width || p.y < 0 || p.y > MAP.height) { guide.textContent = '지금 위치가 이 약도 밖이에요. 출발지를 직접 찾아 골라 주세요.'; return; }
      start = p;
      box.open = false;
      fromInput.value = p.name;
      hits.replaceChildren();
      go();
    }, err => {
      guide.textContent = err.code === 1 ? '위치 권한이 꺼져 있어요. 브라우저 설정에서 켜거나, 출발지를 직접 찾아 골라 주세요.'
        : '위치를 찾지 못했어요. 지하에서는 GPS가 잘 안 잡혀요. 출발지를 직접 찾아 골라 주세요.';
    }, { enableHighAccuracy: true, timeout: 10000 });
  };
}
