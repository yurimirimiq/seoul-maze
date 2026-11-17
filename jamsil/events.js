// 잠실(롯데월드몰)에서 열리는 팝업과 행사 목록.
// 2026-11-17에 롯데월드타워·몰 공식 이벤트 페이지(https://www.lwt.co.kr/ko/event/all.do)의 POP-UP과 MAIN EVENT를 보고 옮겨 적었다.
// shortcut: 손으로 옮긴 스냅샷이라 날짜가 지나면 낡는다. 자주 고치게 되면 자동 수집으로 바꾼다.
// 롯데백화점 잠실점의 팝업은 아직 없다(따로 확인해야 한다). 시작 날짜가 안 나온 행사(달력에 끝나는 날만 있는 것)는 뺐다.
// 형식은 coex/events.js와 같다. at은 팝업이 열리는 자리 바로 옆 가게다('층/가게 이름', stores.js에 적힌 이름).
const EVENTS = [
  { cat: '행사', name: '2026 롯데타운 크리스마스 마켓', start: '2026-11-19', end: '2027-01-03', place: '롯데월드타워·몰', url: 'https://www.lwt.co.kr/ko/event/view.do?seq=1719198' },
  { cat: '팝업', name: '홉티미스트 팝업', start: '2026-11-19', end: '2026-12-02', place: '롯데월드몰 무신사 스탠다드 앞 (지하 1층)', at: 'B1/무신사 스탠다드', url: 'https://www.lwt.co.kr/ko/event/view.do?seq=1696884' },
  { cat: '팝업', name: '조선건어물 팝업', start: '2026-11-03', end: '2026-11-28', place: '롯데월드몰 올리브영 앞 (5층)', at: '5/올리브영' },
  { cat: '팝업', name: 'CONNECT TO', start: '2026-10-23', end: '2026-11-20', place: '롯데월드몰 CONNECT TO (1층)', at: '1/CONNECT TO (렉서스)' },
];
