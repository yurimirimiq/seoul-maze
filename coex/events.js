// 코엑스에서 열리는 행사와 팝업 목록.
// 2026-11-17에 coex.co.kr 행사 일정(2026-11-17 ~ 2026-12-17)을 보고 옮겨 적었다.
// shortcut: 손으로 옮긴 스냅샷이라 날짜가 지나면 낡는다. 자주 고치게 되면 자동 수집으로 바꾼다.
//
// 직접 추가할 때: 아래 형식으로 한 줄을 넣는다.
//   at: 약도에서 점을 찍을 곳. 이름 붙은 건물이면 그 이름, 가게면 '층/가게 이름'(stores.js에 적힌 이름). 안 적으면 코엑스 전시장.
//       가게를 적으면 그 층으로 바뀌면서 찍힌다.
//   url: 자세한 정보 링크. 없으면 빼도 된다.
// 예: { cat: '팝업·이벤트', name: '○○ 팝업', start: '2026-12-01', end: '2026-12-14', place: '별마당도서관 옆', at: 'B1/별마당도서관' },
const EVENTS = [
  {"cat": "컨벤션", "name": "2026 서울시 국제 브리지 대회", "start": "2026-11-16", "end": "2026-11-18", "place": "컨퍼런스룸E (3층)", "url": "https://www.coex.co.kr/exhibitions/2026-서울시-국제-브리지-대회/"},
  {"cat": "팝업·이벤트", "name": "대학내일ES 트렌드 컨퍼런스 2027", "start": "2026-11-17", "end": "2026-11-17", "place": "오디토리움 (3층)", "url": "https://www.coex.co.kr/exhibitions/대학내일es-트렌드-컨퍼런스-2027/"},
  {"cat": "컨벤션", "name": "SMART HOME INTERIOR 2026: 실내건축의 새로운 패러다임", "start": "2026-11-19", "end": "2026-11-19", "place": "컨퍼런스룸(남) 4층", "url": "https://www.coex.co.kr/exhibitions/smart-home-interior-2026-실내건축의-새로운-패러다임/"},
  {"cat": "전시", "name": "제58회 서울국제유아교육전", "start": "2026-11-19", "end": "2026-11-22", "place": "Hall A (1층)", "url": "https://www.coex.co.kr/exhibitions/제58회-서울국제유아교육전/"},
  {"cat": "전시", "name": "글로벌 베이비페어", "start": "2026-11-19", "end": "2026-11-22", "place": "Hall B (1층)", "url": "https://www.coex.co.kr/exhibitions/글로벌-베이비페어/"},
  {"cat": "전시", "name": "2026 트래블 쇼", "start": "2026-11-20", "end": "2026-11-22", "place": "Hall C (3층)", "url": "https://www.coex.co.kr/exhibitions/마인드케어-웰니스-로컬바이브-트래블-쇼/"},
  {"cat": "팝업·이벤트", "name": "2026년 아트프리즘 제3회 아트페어", "start": "2026-11-20", "end": "2026-11-22", "place": "로비", "url": "https://www.coex.co.kr/exhibitions/2026년-아트프리즘-제3회-아트페어/"},
  {"cat": "팝업·이벤트", "name": "2026 소담마켓", "start": "2026-11-20", "end": "2026-11-22", "place": "동문 로비 (1층)", "url": "https://www.coex.co.kr/exhibitions/2026-소담마켓/"},
  {"cat": "컨벤션", "name": "제55회 필리핀유학박람회", "start": "2026-11-21", "end": "2026-11-21", "place": "컨퍼런스룸(남) 3층", "url": "https://www.coex.co.kr/exhibitions/제55회-필리핀유학박람회/"},
  {"cat": "컨벤션", "name": "제436회 웨덱스 웨딩박람회", "start": "2026-11-21", "end": "2026-11-22", "place": "컨퍼런스룸 317~318호 (3층)", "url": "https://www.coex.co.kr/exhibitions/제436회-웨덱스-웨딩박람회/"},
  {"cat": "컨벤션", "name": "2026 블록체인 진흥주간", "start": "2026-11-25", "end": "2026-11-26", "place": "컨퍼런스룸E (3층)", "url": "https://www.coex.co.kr/exhibitions/2026-블록체인-진흥주간/"},
  {"cat": "전시", "name": "소싱인마켓", "start": "2026-11-25", "end": "2026-11-27", "place": "Hall C (3층)", "url": "https://www.coex.co.kr/exhibitions/소싱인마켓/"},
  {"cat": "전시", "name": "디자인코리아 2026", "start": "2026-11-25", "end": "2026-11-29", "place": "Hall B (1층)", "url": "https://www.coex.co.kr/exhibitions/디자인코리아-2026/"},
  {"cat": "컨벤션", "name": "도쿄 기프트쇼 인 서울 2026", "start": "2026-11-25", "end": "2026-11-26", "place": "The Platz (2층)", "url": "https://www.coex.co.kr/exhibitions/도쿄-기프트쇼-인-서울-2026/"},
  {"cat": "전시", "name": "2026 서울디자인페스티벌", "start": "2026-11-26", "end": "2026-11-29", "place": "Hall A (1층)", "url": "https://www.coex.co.kr/exhibitions/2026-서울디자인페스티벌/"},
  {"cat": "컨벤션", "name": "제46회 iBN 호주유학 박람회", "start": "2026-11-28", "end": "2026-11-29", "place": "컨퍼런스룸(남) 3층", "url": "https://www.coex.co.kr/exhibitions/제46회-ibn-호주유학-박람회/"},
  {"cat": "전시", "name": "2026 서울국제발명전시회", "start": "2026-12-02", "end": "2026-12-05", "place": "Hall C (3층)", "url": "https://www.coex.co.kr/exhibitions/2026-서울국제발명전시회/"},
  {"cat": "전시", "name": "2026 대한민국발명특허대전", "start": "2026-12-02", "end": "2026-12-05", "place": "Hall C (3층)", "url": "https://www.coex.co.kr/exhibitions/2026-대한민국발명특허대전/"},
  {"cat": "전시", "name": "2026 상표·디자인권展", "start": "2026-12-02", "end": "2026-12-05", "place": "Hall C (3층)", "url": "https://www.coex.co.kr/exhibitions/2026-상표·디자인권展/"},
  {"cat": "전시", "name": "2026 월드 웹툰 페스티벌", "start": "2026-12-02", "end": "2026-12-06", "place": "Hall B (1층)", "url": "https://www.coex.co.kr/exhibitions/2026-월드-웹툰-페스티벌/"},
  {"cat": "전시", "name": "제11회 대한민국 소프트웨어 대전, 소프트웨이브 2026", "start": "2026-12-02", "end": "2026-12-04", "place": "Hall A (1층)", "url": "https://www.coex.co.kr/exhibitions/제11회-대한민국-소프트웨어-대전-소프트웨이브-2026/"},
  {"cat": "컨벤션", "name": "유학네트 유학박람회", "start": "2026-12-05", "end": "2026-12-05", "place": "컨퍼런스룸(남) 3층", "url": "https://www.coex.co.kr/exhibitions/유학네트-유학박람회-8/"},
  {"cat": "전시", "name": "컴업 2026", "start": "2026-12-09", "end": "2026-12-11", "place": "Hall C (3층)", "url": "https://www.coex.co.kr/exhibitions/컴업-2026/"},
  {"cat": "전시", "name": "2026 코리아 테크 페스티벌", "start": "2026-12-09", "end": "2026-12-11", "place": "Hall B (1층)", "url": "https://www.coex.co.kr/exhibitions/2026-코리아-테크-페스티벌/"},
  {"cat": "전시", "name": "2027학년도 정시 대학입학정보박람회", "start": "2026-12-11", "end": "2026-12-13", "place": "Hall A (1층)", "url": "https://www.coex.co.kr/exhibitions/2026학년도-정시-대학입학정보박람회-2/"},
  {"cat": "전시", "name": "2026 한국국제치과의료기기 전시회 및 학술대회", "start": "2026-12-11", "end": "2026-12-13", "place": "Hall D (3층)", "url": "https://www.coex.co.kr/exhibitions/2026-한국국제치과의료기기-전시회-및-학술대회/"},
  {"cat": "컨벤션", "name": "MSPAC 2026 제8회 메디게이트 성공개원 정보&학술 컨퍼런스", "start": "2026-12-13", "end": "2026-12-13", "place": "컨퍼런스룸E (3층)", "url": "https://www.coex.co.kr/exhibitions/mspac-2026-제8회-메디게이트-성공개원-정보학술-컨퍼런스/"},
  {"cat": "전시", "name": "카카오 비즈니스 페어", "start": "2026-12-13", "end": "2026-12-14", "place": "Hall B (1층)", "url": "https://www.coex.co.kr/exhibitions/카카오-비즈니스-페어/"},
  {"cat": "전시", "name": "2026 K-핸드메이드페어", "start": "2026-12-17", "end": "2026-12-20", "place": "Hall B (1층)", "url": "https://www.coex.co.kr/exhibitions/2026-k-핸드메이드페어/"},
  {"cat": "전시", "name": "2026 홈테이블데코페어", "start": "2026-12-17", "end": "2026-12-20", "place": "Hall C, D (3층)", "url": "https://www.coex.co.kr/exhibitions/2026-홈테이블데코페어/"},
  {"cat": "전시", "name": "2026 공예트렌드페어", "start": "2026-12-17", "end": "2026-12-20", "place": "Hall A (1층)", "url": "https://www.coex.co.kr/exhibitions/2026-공예트렌드페어/"},
];
