// 날짜가 YYYY-MM-DD 글자라서 글자 비교만으로 앞뒤를 가릴 수 있다.
const isOpen = (e, today) => e.start <= today && today <= e.end;
// 'Hall C (3층)' -> ['Hall C', '3'], 층이 안 적힌 곳은 ['로비']
const splitFloor = place => { const m = place.match(/\s*\(?(\d)층\)?/); return m ? [place.replace(m[0], '').trim(), m[1]] : [place]; };
const t = { start: '2026-01-01', end: '2026-01-31' };
console.assert(isOpen(t, '2026-01-01') && isOpen(t, '2026-01-31') && !isOpen(t, '2025-12-31') && !isOpen(t, '2026-02-01'), 'isOpen 자가 점검 실패');
console.assert(splitFloor('Hall C, D (3층)').join() === 'Hall C, D,3' && splitFloor('컨퍼런스룸(남) 4층').join() === '컨퍼런스룸(남),4' && splitFloor('로비').join() === '로비', 'splitFloor 자가 점검 실패');

// 약도 그리기
const svg = document.getElementById('map');
const el = (tag, attrs, text, parent = svg) => {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text) n.textContent = text;
  return parent.appendChild(n);
};
svg.setAttribute('viewBox', `0 0 ${MAP.width} ${MAP.height}`);
for (const b of MAP.buildings) el('polygon', { points: b.pts, class: b.label ? 'main' : '' });

// 역 이름 -> 노선 번호. 새 장소를 넣을 때 그 장소의 역을 여기에 더한다. 노선 색은 style.css에 있다.
const LINES = { '삼성역': '2', '봉은사역': '9' };
for (const s of MAP.spots) {
  const exit = s.name.match(/^(.+역) (.+)번 출구$/);
  if (s.floor) {
    // 층에 딸린 가게는 그 층을 골랐을 때만 점으로 보인다. 이름은 겹치지 않게 고른 것만 띄운다.
    el('circle', { cx: s.x, cy: s.y, r: 1.1, class: 'spot', 'data-floor': s.floor });
  } else if (exit && LINES[exit[1]]) {
    // 지하철 출구는 실제 표지판처럼 그린다: 노선 색 동그라미 + 노란 출구 번호
    const line = LINES[exit[1]];
    const below = s.y > MAP.height / 2; // 이름표가 건물과 겹치지 않게 남쪽 절반은 아래에, 북쪽 절반은 위에 쓴다
    const w = 2 + exit[2].length * 1.7;
    const left = s.x - (4.6 + w) / 2;
    el('circle', { cx: left + 2, cy: s.y, r: 2, class: 'line l' + line });
    el('text', { x: left + 2, y: s.y + 1, class: 'sign l' + line }, line);
    el('rect', { x: left + 4.6, y: s.y - 2, width: w, height: 4, rx: .6, class: 'exit' });
    el('text', { x: left + 4.6 + w / 2, y: s.y + 1, class: 'sign' }, exit[2]);
    el('text', { x: s.x, y: below ? s.y + 5.6 : s.y - 3.2 }, exit[1]);
  } else {
    el('circle', { cx: s.x, cy: s.y, r: 1.1, class: 'spot' });
    el('text', { x: s.x, y: s.y - 1.8 }, s.name);
  }
}
// 건물 이름은 가게 점보다 나중에 그려서 점에 가려지지 않게 한다
for (const b of MAP.buildings) if (b.label) el('text', { x: b.x, y: b.y + 1 }, b.name);
el('path', { d: 'M4 9l2-5 2 5z', class: 'north' });
el('text', { x: 6, y: 12.4, class: 'north' }, '북');
const ping = el('circle', { id: 'ping', r: 2.4, display: 'none' });
const pin = el('circle', { id: 'pin', r: 2.4, display: 'none' });
const pinName = el('text', { id: 'pinname', display: 'none' });
const places = Object.fromEntries([...MAP.buildings, ...MAP.spots].map(p => [p.name, p]));

const add = (parent, tag, text, cls) => {
  const n = parent.appendChild(document.createElement(tag));
  if (text) n.textContent = text;
  if (cls) n.className = cls;
  return n;
};

// 고른 곳에 빨간 점을 찍는다. 행사와 층별 목록의 가게가 같이 쓴다.
const pick = (btn, name) => {
  document.querySelectorAll('.pick').forEach(b => b.setAttribute('aria-pressed', b === btn));
  const p = places[name];
  if (!p) return console.error('약도에 없는 곳:', name);
  const y = p.pts ? p.y + 5 : p.y; // 건물은 가운데 이름표를 가리지 않게 조금 아래에 찍는다
  for (const c of [pin, ping]) {
    c.setAttribute('cx', p.x);
    c.setAttribute('cy', y);
    c.removeAttribute('display');
  }
  // 이름표가 없는 가게는 점 위에 이름을 띄운다
  pinName.textContent = p.floor ? p.name : '';
  pinName.setAttribute('x', Math.min(Math.max(p.x, p.name.length * 1.6), MAP.width - p.name.length * 1.6));
  pinName.setAttribute('y', y - 3.6);
  pinName.removeAttribute('display');
  ping.classList.remove('go');
  ping.getBBox(); // 애니메이션을 처음부터 다시 돌리려면 한 번 읽어 줘야 한다
  ping.classList.add('go');
  svg.scrollIntoView({ block: 'nearest' });
};

// 층 고르기
const floorBtns = document.getElementById('floors');
const panel = document.getElementById('floor');
const setFloor = id => {
  const f = FLOORS.find(f => f.id === id);
  if (!f) return;
  for (const b of floorBtns.children) b.setAttribute('aria-pressed', b.dataset.floor === id);
  for (const n of svg.querySelectorAll('[data-floor]')) n.style.display = n.dataset.floor === id ? '' : 'none';
  for (const n of [pin, ping, pinName]) n.setAttribute('display', 'none');
  document.querySelectorAll('.pick').forEach(b => b.setAttribute('aria-pressed', 'false'));

  panel.replaceChildren();
  add(add(panel, 'h2', f.name), 'small', f.note);
  const rows = add(panel, 'ul', '', 'rows');
  const row = title => { const li = add(rows, 'li'); add(li, 'span', title, 'kind'); return add(li, 'div'); };
  for (const g of f.groups) {
    const box = row(g.title);
    for (const [name, where] of g.items) add(add(box, 'p', name), 'small', where);
  }
  // 이 층에 위치가 있는 가게는 누르면 약도에 찍힌다
  const spots = MAP.spots.filter(s => s.floor === id);
  for (const kind of new Set(spots.map(s => s.kind))) {
    const box = row(kind);
    for (const s of spots.filter(s => s.kind === kind)) {
      const btn = add(box, 'button', s.name, 'pick');
      btn.setAttribute('aria-pressed', 'false');
      btn.onclick = () => pick(btn, s.name);
    }
  }
};
for (const f of FLOORS) {
  const b = add(floorBtns, 'button', f.id);
  b.dataset.floor = f.id;
  b.setAttribute('aria-label', f.name);
  b.onclick = () => setFloor(f.id);
}
setFloor(FLOORS.at(-1).id); // 맨 아래층(몰)부터 보여 준다

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
    const [place, floor] = splitFloor(e.place);
    const what = add(btn, 'span', '', 'what');
    add(what, 'b', e.name);
    add(add(what, 'small'), 'span', place).after(e.cat);
    if (floor) add(btn, 'span', floor + '층', 'floor');
    btn.onclick = () => {
      if (floor) setFloor(floor); // 행사가 열리는 층으로 같이 바꾼다
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
