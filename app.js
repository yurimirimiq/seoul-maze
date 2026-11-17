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

// 가게 종류별 점 색. 종류 이름은 stores.js와 poi.tsv에 적힌 그대로다. 앞에 있을수록 이름표가 먼저 나온다.
const KINDS = {
  '엔터테인먼트': '#7c5cd6', '서비스': '#5b6b85', '라이프스타일': '#2f9a6a', '패션의류': '#3d7fd0', '레스토랑&카페': '#ef8a2b',
  '패션잡화': '#5a66cf', '뷰티': '#dc5a9a', '홈퍼니싱': '#9a7440', '키즈': '#d9a514', '편의시설': '#9aa3b5',
};
// 역 이름 -> 노선 번호. 새 장소를 넣을 때 그 장소의 역을 여기에 더한다. 노선 색은 style.css에 있다.
const LINES = { '삼성역': '2', '봉은사역': '9' };

// 약도 그리기: 길 -> 건물 -> 실내 칸 -> 이름표 순서로 쌓는다
const svg = document.getElementById('map');
const el = (tag, attrs, text, parent = svg) => {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text) n.textContent = text;
  return parent.appendChild(n);
};
svg.setAttribute('viewBox', `0 0 ${MAP.width} ${MAP.height}`);
for (const r of MAP.roads) el('polyline', { points: r.pts, 'stroke-width': r.w, class: r.w >= 2.5 ? 'road big' : 'road' });
for (const pts of MAP.blocks) el('polygon', { points: pts, class: 'block' });
for (const b of MAP.buildings) el('polygon', { points: b.pts });
// 실내: 층마다 흰 바닥 위에 가게 칸을 얹는다. 칸 사이에 남는 흰 곳이 통로다. 고른 층 것만 보인다.
// 자료에 바닥 모양은 없고 벽 조각만 있어서, 모든 칸을 굵은 흰 테두리로 한 번 깔아 통로까지 하얗게 메운다.
// 칸은 가게 종류 색을 옅게 칠한다(--tint). 종류를 모르는 가게는 style.css의 기본색, 화장실 같은 시설은 회색이다.
const rooms = {};
for (const [id, list] of Object.entries(MAP.shapes || {})) {
  const g = el('g', { class: 'floorplan' });
  el('path', { d: list.map(([, pts]) => 'M' + pts.replaceAll(' ', 'L') + 'Z').join(''), class: 'ground' }, '', g);
  rooms[id] = el('g', { class: 'rooms' }, '', g);
  for (const [kind, pts] of list) {
    const room = el('polygon', { points: pts, class: { '바닥': 'wall', '기타': 'etc' }[kind] || '' }, '', rooms[id]);
    const tint = KINDS[kind] || (kind !== '가게' && KINDS['편의시설']);
    if (tint) room.style.setProperty('--tint', tint);
  }
}
for (const n of MAP.roadNames) el('text', { x: n.x, y: n.y, class: 'roadname', transform: `rotate(${n.rot} ${n.x} ${n.y})` }, n.name);

const signs = []; // 늘 보이는 것들이 차지한 자리. 가게 이름표가 이 위에 겹치지 않게 한다.
const kindOrder = Object.keys(KINDS);
const stores = MAP.spots.filter(s => s.floor).sort((a, b) => kindOrder.indexOf(a.kind) - kindOrder.indexOf(b.kind));
for (const s of stores) {
  s.room = rooms[s.floor]?.children[s.shape]; // 이 가게가 차지한 칸. 칸이 없는 곳만 점으로 찍는다.
  if (!s.room) s.dot = el('circle', { cx: s.x, cy: s.y, r: .7, fill: KINDS[s.kind] || KINDS['서비스'], class: 'spot' });
}
for (const b of MAP.buildings) { el('text', { x: b.x, y: b.y, class: 'bname' }, b.name); signs.push({ x: b.x, y: b.y, name: b.name }); }
for (const s of stores) s.label = el('text', { x: s.x, y: s.y, dx: s.room ? 0 : '.8em', class: 'spotname' + (s.room ? ' mid' : '') + (s.kind === '편의시설' ? ' minor' : '') }, s.name);
for (const s of MAP.spots.filter(s => !s.floor)) {
  const exit = s.name.match(/^(.+역) (.+)번 출구$/);
  if (!exit || !LINES[exit[1]]) { el('text', { x: s.x, y: s.y, class: 'bname' }, s.name); continue; }
  // 지하철 출구는 실제 표지판처럼 그린다: 노선 색 동그라미 + 노란 출구 번호
  const line = LINES[exit[1]];
  const below = s.y > MAP.height / 2; // 이름이 건물과 겹치지 않게 남쪽 절반은 아래에, 북쪽 절반은 위에 쓴다
  const w = 2 + exit[2].length * 1.7;
  const left = s.x - (4.6 + w) / 2;
  const g = el('g', { class: 'keep' }); // 표지판은 약도를 키워도 같은 크기로 남는다
  el('circle', { cx: left + 2, cy: s.y, r: 2, class: 'line l' + line }, '', g);
  el('text', { x: left + 2, y: s.y + 1, class: 'sign l' + line }, line, g);
  el('rect', { x: left + 4.6, y: s.y - 2, width: w, height: 4, rx: .6, class: 'exit' }, '', g);
  el('text', { x: left + 4.6 + w / 2, y: s.y + 1, class: 'sign' }, exit[2], g);
  el('text', { x: s.x, y: below ? s.y + 5.6 : s.y - 3.2, class: 'fixed' }, exit[1], g);
  signs.push({ x: s.x, y: s.y, name: exit[1] + '  ' });
}
const ping = el('circle', { id: 'ping', r: 2.4, display: 'none' });
const pin = el('circle', { id: 'pin', r: 2.4, class: 'keep', display: 'none' });

// 이름으로 찾기. 건물은 이름, 가게는 '층/이름'. 화장실처럼 같은 이름이 여러 곳이면 다 담긴다.
const places = {};
for (const b of MAP.buildings) places[b.name] = [b];
for (const s of stores) (places[s.floor + '/' + s.name] ||= []).push(s);

const add = (parent, tag, text, cls) => {
  const n = parent.appendChild(document.createElement(tag));
  if (text) n.textContent = text;
  if (cls) n.className = cls;
  return n;
};

// 약도 키우기와 줄이기. 손가락으로 끌면 옮겨진다.
const scroller = document.getElementById('mapscroll');
const [zoomIn, zoomOut] = document.querySelectorAll('.zoom button');
scroller.style.aspectRatio = `${MAP.width} / ${MAP.height}`;
const MAX_ZOOM = 8;
let zoom = 1, floor, picked = [];

// 지금 층의 가게 이름표 가운데 서로 겹치지 않는 것만 보여 준다. 키울수록 더 많이 보인다.
const relabel = () => {
  const px = svg.clientWidth / MAP.width; // 약도 1칸이 화면에서 몇 px인지
  const font = 3 * px / zoom;             // 글자 크기는 키워도 그대로다
  const width = name => [...name].reduce((w, ch) => w + (ch.charCodeAt(0) < 128 ? .6 : 1), 0) * font;
  const kept = signs.map(g => ({ x: g.x * px - width(g.name) / 2, y: g.y * px - font * .7, w: width(g.name), h: font * 1.4 }));
  // 편의시설 이름은 목록에서 골랐을 때만 보인다. 늘 보이면 가게 이름과 섞여 어지럽다.
  const shown = s => s.floor === floor && (s.kind !== '편의시설' || picked.includes(s));
  for (const s of stores) {
    s.label.style.display = 'none';
    if (s.dot) s.dot.style.display = shown(s) ? '' : 'none';
  }
  for (const s of [...picked.filter(shown), ...stores.filter(s => shown(s) && !picked.includes(s))]) {
    // 이름이 차지할 자리에 숨 쉴 틈을 조금 둔다. 칸이 있는 가게는 가운데 정렬, 점만 있는 곳은 점 오른쪽.
    const w = width(s.name) + font * (s.room ? .8 : 1.6);
    const box = { x: s.x * px - (s.room ? w / 2 : 0), y: s.y * px - font * .9, w, h: font * 1.8 };
    const show = picked.includes(s) || !kept.some(k => overlaps(k, box));
    s.label.style.display = show ? '' : 'none';
    if (show) kept.push(box);
  }
};
// at: 그 자리가 움직이지 않게 키울 화면 위치(스크롤 상자 기준). 안 주면 가운데.
const setZoom = (z, at = { x: scroller.clientWidth / 2, y: scroller.clientHeight / 2 }) => {
  const mx = (scroller.scrollLeft + at.x) / zoom, my = (scroller.scrollTop + at.y) / zoom;
  zoom = Math.min(MAX_ZOOM, Math.max(1, z));
  svg.style.width = zoom * 100 + '%';
  svg.style.setProperty('--z', zoom); // 글자와 점은 약도가 커져도 같은 크기로 남는다
  scroller.scrollTo(mx * zoom - at.x, my * zoom - at.y);
  zoomIn.disabled = zoom === MAX_ZOOM;
  zoomOut.disabled = zoom === 1;
  relabel();
};
zoomIn.onclick = () => setZoom(zoom * 2);
zoomOut.onclick = () => setZoom(zoom / 2);
// 마우스 휠이나 트랙패드로도 키우고 줄인다. 커서가 있는 자리를 중심으로 움직인다.
scroller.addEventListener('wheel', e => {
  const next = Math.min(MAX_ZOOM, Math.max(1, zoom * Math.exp(-e.deltaY * (e.ctrlKey ? .01 : .002)))); // ctrlKey = 트랙패드 두 손가락 벌리기
  if (next === zoom) return; // 더 줄일 수 없으면 페이지가 평소처럼 스크롤되게 둔다
  e.preventDefault();
  const box = scroller.getBoundingClientRect();
  setZoom(next, { x: e.clientX - box.left, y: e.clientY - box.top });
}, { passive: false });
// 폰에서는 두 손가락을 벌리거나 오므려서 키우고 줄인다. 두 손가락의 가운데를 중심으로 움직인다.
let pinch;
const spread = e => Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
scroller.addEventListener('touchstart', e => { pinch = e.touches.length === 2 ? { spread: spread(e), zoom } : null; });
scroller.addEventListener('touchmove', e => {
  if (!pinch || e.touches.length !== 2) return;
  e.preventDefault(); // 페이지 전체가 커지는 것을 막는다
  const box = scroller.getBoundingClientRect();
  setZoom(pinch.zoom * spread(e) / pinch.spread, {
    x: (e.touches[0].clientX + e.touches[1].clientX) / 2 - box.left,
    y: (e.touches[0].clientY + e.touches[1].clientY) / 2 - box.top });
}, { passive: false });
scroller.addEventListener('touchend', () => { pinch = null; });
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
const setFloor = id => {
  const f = FLOORS.find(f => f.id === id);
  if (!f) return;
  floor = id;
  for (const b of floorBtns.children) b.setAttribute('aria-pressed', b.dataset.floor === id);
  for (const f in rooms) rooms[f].parentNode.style.display = f === id ? '' : 'none';
  pick(null, ''); // 다른 층에서 고른 표시를 지운다

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
  const amenities = [...new Set(stores.filter(s => s.floor === id && s.kind === '편의시설').map(s => s.name))];
  if (amenities.length) cats.push(['편의시설', amenities]);
  if (!cats.length) return;
  add(panel, 'h3', total ? `가게 ${total}곳` : '편의시설');
  for (const [i, [cat, names]] of cats.entries()) {
    const box = add(panel, 'details');
    box.setAttribute('name', 'cat'); // 같은 name끼리는 하나만 펼쳐진다
    box.open = i === 0;
    const head = add(box, 'summary');
    add(head, 'i').style.background = KINDS[cat] || KINDS['서비스'];
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
setZoom(1);
addEventListener('resize', relabel);

// 행사 목록
const today = new Date().toLocaleDateString('sv'); // 'sv' 형식 = 내 시간대 기준 YYYY-MM-DD
const day = d => d.slice(5).replace('-', '.');
const fill = (id, events, emptyText, dateText) => {
  const list = document.getElementById(id);
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
fill('now', EVENTS.filter(e => isOpen(e, today)).sort(byStart), '지금 열리는 행사가 없어요.',
  e => e.end === today ? ['오늘', '까지'] : [day(e.end), '까지']);
fill('soon', EVENTS.filter(e => e.start > today).sort(byStart), '예정된 행사가 없어요.',
  e => [day(e.start), e.end === e.start ? '하루만' : '~ ' + day(e.end)]);
