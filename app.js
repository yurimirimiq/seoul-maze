// 날짜가 YYYY-MM-DD 글자라서 글자 비교만으로 앞뒤를 가릴 수 있다.
const isOpen = (e, today) => e.start <= today && today <= e.end;
// 'Hall C (3층)' -> ['Hall C', '3'], 층이 안 적힌 곳은 ['로비']
const splitFloor = place => { const m = place.match(/\s*\(?(\d)층\)?/); return m ? [place.replace(m[0], '').trim(), m[1]] : [place]; };
const t = { start: '2026-01-01', end: '2026-01-31' };
console.assert(isOpen(t, '2026-01-01') && isOpen(t, '2026-01-31') && !isOpen(t, '2025-12-31') && !isOpen(t, '2026-02-01'), 'isOpen 자가 점검 실패');
console.assert(splitFloor('Hall C, D (3층)').join() === 'Hall C, D,3' && splitFloor('컨퍼런스룸(남) 4층').join() === '컨퍼런스룸(남),4' && splitFloor('로비').join() === '로비', 'splitFloor 자가 점검 실패');

// 약도 그리기
const svg = document.getElementById('map');
const el = (tag, attrs, text) => {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text) n.textContent = text;
  return svg.appendChild(n);
};
svg.setAttribute('viewBox', `0 0 ${MAP.width} ${MAP.height}`);
for (const b of MAP.buildings) el('polygon', { points: b.pts, class: b.label ? 'main' : '' });
for (const b of MAP.buildings) if (b.label) el('text', { x: b.x, y: b.y + 1 }, b.name);

// 지하철 출구는 실제 표지판처럼 그린다: 노선 색 동그라미 + 노란 출구 번호
// 역 이름 -> 노선 번호. 새 장소를 넣을 때 그 장소의 역을 여기에 더한다. 노선 색은 style.css에 있다.
const LINES = { '삼성역': '2', '봉은사역': '9' };
for (const s of MAP.spots) {
  const below = s.y > MAP.height / 2; // 이름표가 겹치지 않게 남쪽 절반은 아래에, 북쪽 절반은 위에 쓴다
  const exit = s.name.match(/^(.+역) (.+)번 출구$/);
  if (exit && LINES[exit[1]]) {
    const line = LINES[exit[1]];
    const w = 2 + exit[2].length * 1.7;
    const left = s.x - (4.6 + w) / 2;
    el('circle', { cx: left + 2, cy: s.y, r: 2, class: 'line l' + line });
    el('text', { x: left + 2, y: s.y + 1, class: 'sign l' + line }, line);
    el('rect', { x: left + 4.6, y: s.y - 2, width: w, height: 4, rx: .6, class: 'exit' });
    el('text', { x: left + 4.6 + w / 2, y: s.y + 1, class: 'sign' }, exit[2]);
    el('text', { x: s.x, y: below ? s.y + 5.6 : s.y - 3.2 }, exit[1]);
  } else {
    el('circle', { cx: s.x, cy: s.y, r: 1, class: 'spot' });
    el('text', { x: s.x, y: below ? s.y + 3.8 : s.y - 1.8 }, s.name);
  }
}
el('path', { d: `M${MAP.width - 6} 9l2-5 2 5z`, fill: '#fff' });
el('text', { x: MAP.width - 4, y: 12.4, class: 'north' }, '북');
const ping = el('circle', { id: 'ping', r: 2.4, display: 'none' });
const pin = el('circle', { id: 'pin', r: 2.4, display: 'none' });
const places = Object.fromEntries([...MAP.buildings, ...MAP.spots].map(p => [p.name, p]));

// 행사 목록
const today = new Date().toLocaleDateString('sv'); // 'sv' 형식 = 내 시간대 기준 YYYY-MM-DD
const day = d => d.slice(5).replace('-', '.');
const add = (parent, tag, text, cls) => {
  const n = parent.appendChild(document.createElement(tag));
  if (text) n.textContent = text;
  if (cls) n.className = cls;
  return n;
};
const fill = (id, events, emptyText, dateText) => {
  const list = document.getElementById(id);
  if (!events.length) add(list, 'li', emptyText);
  for (const e of events) {
    const li = add(list, 'li');
    const btn = add(li, 'button');
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
      document.querySelectorAll('.events button').forEach(b => b.setAttribute('aria-pressed', b === btn));
      const p = places[e.at || MAP.main];
      if (!p) return console.error('약도에 없는 곳:', e.at);
      for (const c of [pin, ping]) {
        c.setAttribute('cx', p.x);
        c.setAttribute('cy', p.y + 5); // 이름표를 가리지 않게 조금 아래에 찍는다
        c.removeAttribute('display');
      }
      ping.classList.remove('go');
      ping.getBBox(); // 애니메이션을 처음부터 다시 돌리려면 한 번 읽어 줘야 한다
      ping.classList.add('go');
      svg.scrollIntoView({ block: 'nearest' });
    };
    if (e.url) add(li, 'a', '공식 안내 보기').href = e.url;
  }
};
const byStart = (a, b) => a.start.localeCompare(b.start);
fill('now', EVENTS.filter(e => isOpen(e, today)).sort(byStart), '지금 열리는 행사가 없어요.',
  e => e.end === today ? ['오늘', '까지'] : [day(e.end), '까지']);
fill('soon', EVENTS.filter(e => e.start > today).sort(byStart), '예정된 행사가 없어요.',
  e => [day(e.start), e.end === e.start ? '하루만' : '~ ' + day(e.end)]);
