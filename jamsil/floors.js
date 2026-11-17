// 잠실 층별 안내. 위층부터 적는다. 화면의 층 버튼도 이 순서로 나온다.
// 롯데백화점, 롯데월드몰(에비뉴엘·타워 포함), 캐슬플라자의 같은 층을 한 장에 합쳤다.
// 가게는 여기 적지 않는다. stores.js에서 같은 층 id로 자동으로 붙는다. start: true인 층을 처음에 보여 준다.
const FLOORS = [
  { id: '31', name: '31층', note: '롯데월드타워', groups: [] },
  { id: '12', name: '12층', note: '', groups: [] },
  { id: '11', name: '11층', note: '', groups: [] },
  { id: '10', name: '10층', note: '', groups: [] },
  { id: '9', name: '9층', note: '', groups: [] },
  { id: '8', name: '8층', note: '', groups: [] },
  { id: '7', name: '7층', note: '', groups: [] },
  { id: '6', name: '6층', note: '', groups: [] },
  { id: '5', name: '5층', note: '', groups: [] },
  { id: '4', name: '4층', note: '', groups: [] },
  { id: '3', name: '3층', note: '', groups: [] },
  { id: '2', name: '2층', note: '', groups: [] },
  { id: '1', name: '1층', note: '', groups: [] },
  { id: 'B1', name: '지하 1층', note: '잠실역과 이어지는 층', start: true, groups: [] },
  { id: 'B2', name: '지하 2층', note: '', groups: [] },
];
