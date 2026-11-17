// 고속터미널(신세계백화점 강남점) 층별 안내. 위층부터 적는다. 화면의 층 버튼도 이 순서로 나온다.
// 층 설명은 신세계백화점 공식 층별 안내의 층 이름이다. 매장은 stores.js에서 같은 층 id로 자동으로 붙는다.
// start: true인 층을 처음에 보여 준다.
const FLOORS = [
  { id: '11', name: '11층', note: "S GARDEN, 전문식당가", groups: [] },
  { id: '10', name: '10층', note: "리틀신세계(아동,유아), 란제리", groups: [] },
  { id: '9', name: '9층', note: "가구, 홈패션, 가전, 키친웨어", groups: [] },
  { id: '8', name: '8층', note: "뉴스트리트, 베이직 스포츠, 스포츠, 아웃도어", groups: [] },
  { id: '7', name: '7층', note: "골프, 남성 캐주얼, 남성 컨템포러리, 정장", groups: [] },
  { id: '6', name: '6층', note: "남성 부티크", groups: [] },
  { id: '5', name: '5층', note: "여성 클래식, 뉴 컨템포러리, 핸드백", groups: [] },
  { id: '4', name: '4층', note: "해외 컨템포러리, 슈즈", groups: [] },
  { id: '3', name: '3층', note: "인터내셔널 디자이너, 럭셔리 워치&주얼리", groups: [] },
  { id: '2', name: '2층', note: "해외유명브랜드", groups: [] },
  { id: '1M', name: '1층 위 중층 (1M)', note: "액세서리, 여행, F&B, 하우스오브신세계 (ART&LIFE, 카페)", groups: [] },
  { id: '1', name: '1층', note: "화장품, 해외유명브랜드, 잡화, 와인셀라 &레스토랑", start: true, groups: [] },
  { id: 'B1', name: '지하 1층', note: "신세계 마켓, 스위트 파크, 푸드홀, 팩토리스토어", groups: [] },
];
