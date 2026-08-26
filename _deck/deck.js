// 최종발표 자료 — Prefab (창업 C-06 전전컴)
//
// **디자인 규칙 하나: 색을 바닥에 깔지 않는다.**
//
// 앞판은 표지·6번·15번이 #1B64DA 전면이었다. 같은 파랑이라도 화면 전체를 덮으면
// 무겁게 읽힌다. Stripe·Linear 같은 곳을 훑어봐도 색은 바닥이 아니라 **악센트**로
// 쓴다 — 밝은 바탕 위에 글자 몇 개, 칩 하나, 카드 테두리.
//
// 그리고 그 답은 이미 우리 서비스에 있었다. prefab-web 의 색과 카드 모양을
// 그대로 가져온다. 발표와 데모의 생김새가 다르면 다른 물건으로 보인다.

const pptxgen = require("pptxgenjs");
const fs = require("fs");

/** PNG 머리에서 가로·세로를 읽는다. 비율을 지켜 넣으려고 쓴다. */
function sizeOf(file) {
  const b = fs.readFileSync(file);
  return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.author = "전전컴 (C-06)";
pres.title = "Prefab — 보드를 발주하기 전에";

const W = 13.33;
const H = 7.5;

// prefab-web 의 tailwind.config.js 에서 그대로 가져온 값
const INK = "191F28";
const SUB = "4E5968";
const MUTE = "8B95A1";
const LINE = "E5E8EB";
const BG = "F7F8FA";
const CARD = "FFFFFF";
const SUNK = "F2F4F6";
const BLUE = "1B64DA";
const BLUE_SOFT = "EBF3FE";
const CRIT = "D6293E";
const CRIT_SOFT = "FEECEE";
const OK = "087A57";
const OK_SOFT = "E6F7F1";
const WARN = "B45309";
const WARN_SOFT = "FFF4E5";

// 서비스가 쓰는 글씨체. 코드는 Office 에 늘 있는 Consolas 로 둔다 —
// 라틴 문자뿐이라 대체돼도 티가 안 난다.
const F = "Pretendard";
const MONO = "Consolas";

const soft = () => ({ type: "outer", blur: 18, offset: 2, angle: 90, color: INK, opacity: 0.06 });

const DECK = [];

function slide() {
  const s = pres.addSlide();
  s.background = { color: BG };
  DECK.push(s);
  return s;
}

/** 꼬리말과 쪽 번호 — 원본과 같은 자리, 같은 색 */
function chrome(s, given) {
  s.addText("●–○  Prefab", {
    x: 0.7, y: H - 0.44, w: 2.2, h: 0.3,
    fontFace: F, fontSize: 10.5, bold: true, color: MUTE, isTextBox: true, margin: 0,
  });
  // **번호를 손으로 넘기지 않는다.** 장을 하나 빼면 뒤가 전부 어긋난다 —
  // 실제로 9번을 빼면서 그럴 뻔했다. 넘어온 값이 없으면 지금까지 만든 장 수를 쓴다.
  const page = given ?? DECK.length;
  if (page) {
    s.addText(String(page).padStart(2, "0"), {
      x: W - 1.2, y: H - 0.44, w: 0.5, h: 0.3, align: "right",
      fontFace: F, fontSize: 10, color: "B7C0CC", isTextBox: true, margin: 0,
    });
  }
}

/**
 * 제목. **밑줄도 색막대도 쓰지 않는다** — 그건 만든 티가 나는 장식이다.
 * 강조는 색 하나로만 준다.
 */
function title(s, runs, opts = {}) {
  s.addText(runs, {
    x: 0.9, y: opts.y ?? 0.72, w: W - 1.8, h: opts.h ?? 1.35,
    fontFace: F, fontSize: opts.size ?? 30, bold: true, color: INK,
    isTextBox: true, margin: 0, lineSpacing: opts.lineSpacing ?? 40, valign: "top",
  });
}

function kicker(s, text) {
  s.addText(text, {
    x: 0.9, y: 0.44, w: W - 1.8, h: 0.26,
    fontFace: F, fontSize: 11.5, bold: true, color: BLUE,
    charSpacing: 1.2, isTextBox: true, margin: 0,
  });
}

function card(s, x, y, w, h, fill) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.14,
    fill: { color: fill || CARD },
    line: fill && fill !== CARD ? { type: "none" } : { color: LINE, width: 1 },
    shadow: fill && fill !== CARD ? undefined : soft(),
  });
}

function chip(s, x, y, text, fg, bg) {
  const w = Math.max(0.55, 0.155 * text.length + 0.34);
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 0.32, rectRadius: 0.08, fill: { color: bg }, line: { type: "none" },
  });
  s.addText(text, {
    x, y, w, h: 0.32, align: "center", valign: "middle",
    fontFace: F, fontSize: 11, bold: true, color: fg, isTextBox: true, margin: 0,
  });
  return w;
}

function mono(s, x, y, w, h, runs, opts = {}) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.1, fill: { color: opts.fill || SUNK }, line: { type: "none" },
  });
  s.addText(runs, {
    x: x + 0.26, y: y + 0.18, w: w - 0.52, h: h - 0.36,
    fontFace: MONO, fontSize: opts.size ?? 12.5, color: opts.color || INK,
    isTextBox: true, margin: 0, lineSpacing: opts.lineSpacing ?? 20, valign: "top",
  });
}

function body(s, x, y, w, h, runs, opts = {}) {
  s.addText(runs, {
    x, y, w, h, fontFace: F, fontSize: opts.size ?? 14.5, color: opts.color || SUB,
    isTextBox: true, margin: 0, lineSpacing: opts.lineSpacing ?? 23,
    valign: opts.valign || "top", align: opts.align,
  });
}

/** 큰 숫자 하나 + 라벨. 표보다 이게 멀리서 읽힌다. */
function stat(s, x, y, w, value, unit, label, color) {
  s.addText(
    [
      { text: value, options: { fontSize: 40, bold: true, color: color || INK } },
      { text: unit ? unit : "", options: { fontSize: 15, bold: true, color: MUTE } },
    ],
    { x, y, w, h: 0.78, fontFace: F, isTextBox: true, margin: 0 }
  );
  s.addText(label, {
    x, y: y + 0.76, w, h: 0.3,
    fontFace: F, fontSize: 11.5, color: MUTE, isTextBox: true, margin: 0,
  });
}

/** 문장 한 줄만 있는 슬라이드. 전면 파랑 대신 **여백**으로 세운다. */
function statement(s, runs, opts = {}) {
  s.addText(runs, {
    x: 1.1, y: opts.y ?? 2.35, w: W - 2.2, h: opts.h ?? 2.8,
    fontFace: F, fontSize: opts.size ?? 40, bold: true, color: INK,
    isTextBox: true, margin: 0, lineSpacing: opts.lineSpacing ?? 56, valign: "middle",
  });
}

// ══════════════════════════════════════════════════ 01 표지
{
  const s = slide();
  chip(s, 0.9, 1.28, "회로도 ↔ 펌웨어 대조 검사", BLUE, BLUE_SOFT);

  s.addText("●–○  Prefab", {
    x: 0.9, y: 1.9, w: 5.5, h: 0.8,
    fontFace: F, fontSize: 44, bold: true, color: INK, isTextBox: true, margin: 0,
  });

  s.addText(
    [
      { text: "보드를 발주하기 전에,", options: { color: INK, breakLine: true } },
      { text: "코드와 회로도가 어긋난 곳을 찾습니다.", options: { color: BLUE } },
    ],
    {
      x: 0.9, y: 3.02, w: 6.7, h: 1.7,
      fontFace: F, fontSize: 24, bold: true, isTextBox: true, margin: 0, lineSpacing: 36,
    }
  );

  body(s, 0.9, 4.85, 6.6, 0.9,
    "컴파일도 되고 업로드도 되는데\n보드가 안 도는 버그를 잡습니다.", { size: 15 });

  s.addImage({ path: "finding-card.png", x: 7.7, y: 1.75, w: 4.73, h: 3.28, shadow: soft() });

  s.addText("2026 PNU 창의융합AI해커톤 · 창업트랙 C-06 전전컴", {
    x: 0.9, y: 6.5, w: 6.7, h: 0.3,
    fontFace: F, fontSize: 11.5, bold: true, color: MUTE, isTextBox: true, margin: 0,
  });
  s.addText("prefab-web.onrender.com", {
    x: W - 5.4, y: 6.5, w: 4.5, h: 0.3, align: "right",
    fontFace: MONO, fontSize: 11.5, color: BLUE, isTextBox: true, margin: 0,
  });
}

// ══════════════════════════════════════════════════ 02 어긋난 코드
{
  const s = slide();
  kicker(s, "실제로 찾은 것");
  title(s, [
    { text: "한 줄만 안 따라왔습니다.", options: { breakLine: true } },
    { text: "그리고 25번은 이제 데이터선입니다.", options: { color: BLUE } },
  ]);

  card(s, 0.9, 2.35, 11.53, 2.5);
  mono(s, 1.25, 2.7, 10.83, 1.8, [
    { text: "#define TFT_BL     19", options: { bold: true, color: INK } },
    { text: "   // Swapped with MISO to match soldered E1 wiring", options: { color: MUTE, breakLine: true } },
    { text: "#define TFT_BL_PIN 25", options: { bold: true, color: CRIT } },
    { text: "   // Backlight PWM", options: { color: MUTE } },
  ], { size: 14, lineSpacing: 30 });

  body(s, 0.9, 5.15, 11.53, 1.1, [
    { text: "납땜에 맞춰 백라이트를 19번으로 옮겨 뒀는데, 다른 파일의 상수는 25번에 그대로 남았습니다. ", options: {} },
    { text: "컴파일도 되고 업로드도 됩니다.", options: { bold: true, color: INK, breakLine: true } },
    { text: "GitHub 공개 저장소 FForzano/xgsail-e1 (Apache-2.0)", options: { size: 12, color: MUTE } },
  ], { size: 14.5 });
  chrome(s);
}

// ══════════════════════════════════════════════════ 03 비용
{
  const s = slide();
  kicker(s, "왜 비싼가");
  title(s, [
    { text: "소프트웨어는 다시 배포하면 됩니다.", options: { breakLine: true } },
    { text: "하드웨어는 돈이 사라집니다.", options: { color: CRIT } },
  ]);

  const cells = [
    ["2.9", "회", "평균 재작업 횟수", INK],
    ["약 6,000", "만원", "1회당 비용", CRIT],
    ["8.5", "일", "1회당 지연", INK],
  ];
  cells.forEach(([v, u, l, c], i) => {
    const x = 0.9 + i * 3.93;
    card(s, x, 2.55, 3.67, 1.85);
    stat(s, x + 0.4, 2.85, 3.0, v, u, l, c);
  });

  body(s, 0.9, 4.75, 11.53, 0.6,
    "Lifecycle Insights, PCB 설계 프로젝트 조사", { size: 12, color: MUTE });

  card(s, 0.9, 5.35, 11.53, 1.15, BLUE_SOFT);
  body(s, 1.3, 5.35, 10.73, 1.15, [
    { text: "저희가 줄이려는 건 이 숫자입니다. ", options: { bold: true, color: INK, size: 15 } },
    { text: "보드가 도착하기 전에 알면, 재작업 자체가 없습니다.", options: { size: 14 } },
  ], { valign: "middle" });
  chrome(s);
}

// ══════════════════════════════════════════════════ 04 서울시
{
  const s = slide();
  kicker(s, "우리만 그렇게 보는 게 아닙니다");
  title(s, [{ text: "서울시는 이 문제에 세금을 쓰고 있습니다." }], { h: 0.9 });

  card(s, 0.9, 1.95, 11.53, 1.5);
  body(s, 1.35, 1.95, 10.63, 1.5, [
    { text: "“위험부담을 감수하고 제품개발에 도전해야 하므로 진입장벽이 크다”", options: { bold: true, color: INK, size: 17, breakLine: true } },
    { text: "— 서울특별시 경제정책실 창업정책과, 2025.02", options: { size: 12.5, color: MUTE } },
  ], { valign: "middle", lineSpacing: 27 });

  const cells = [
    ["64", "개", "2023년 지원 기업", INK],
    ["235", "건", "시제품 제작", INK],
    ["−17", "%", "2024년 초기 스타트업 투자", CRIT],
  ];
  cells.forEach(([v, u, l, c], i) => {
    const x = 0.9 + i * 3.93;
    card(s, x, 3.7, 3.67, 1.85);
    stat(s, x + 0.4, 4.0, 3.1, v, u, l, c);
  });

  body(s, 0.9, 5.85, 11.53, 0.6,
    "지원은 만들어 주는 것이지, 틀린 걸 미리 잡아 주지는 않습니다.", { size: 14.5, color: INK });
  chrome(s);
}

// ══════════════════════════════════════════════════ 05 빈자리 (전면 이미지)
{
  const s = slide();
  s.background = { color: "FFFFFF" };
  s.addImage({ path: "gap.png", x: 0, y: 0, w: W, h: H });
  chrome(s);
}

// ══════════════════════════════════════════════════ 06 한 문장
{
  const s = slide();
  kicker(s, "저희가 하는 일");
  statement(s, [
    { text: "이미 짜 놓은 펌웨어가", options: { breakLine: true } },
    { text: "바뀐 회로도를 따라가고 있는지", options: { breakLine: true } },
    { text: "검사합니다.", options: { color: BLUE } },
  ], { y: 1.9, h: 3.6, size: 38, lineSpacing: 58 });

  const three = ["회로도 — 어느 핀이 어디에 이어졌는지",
                 "펌웨어 — 코드가 그 핀을 어떻게 쓰는지",
                 "데이터시트 — 그 부품이 견디는 값"];
  three.forEach((t, i) => {
    const x = 0.9 + i * 3.93;
    card(s, x, 5.5, 3.67, 0.86, CARD);
    body(s, x + 0.32, 5.5, 3.03, 0.86, t, { size: 12, valign: "middle", lineSpacing: 16 });
  });
  chrome(s);
}

// ══════════════════════════════════════════════════ 07 발견 카드
{
  const s = slide();
  kicker(s, "2장의 그 저장소를 그대로 넣었습니다");
  title(s, [
    { text: "판정마다 " },
    { text: "근거", options: { color: BLUE } },
    { text: "가 붙습니다." },
  ], { h: 0.9 });

  s.addImage({ path: "finding.png", x: 0.9, y: 1.85, w: 7.9, h: 5.47, shadow: soft() });

  const rows = [
    ["회로도가 아는 것", "어느 네트에 무엇이 물렸는지", OK, OK_SOFT, "읽음"],
    ["코드가 아는 것", "파일 이름과 줄 번호까지", OK, OK_SOFT, "읽음"],
    ["부품이 아는 것", "확인 못 했으면 그렇게 적습니다", MUTE, SUNK, "모름"],
  ];
  let y = 2.0;
  rows.forEach(([h, d, fg, bg, tag]) => {
    card(s, 9.1, y, 3.33, 1.18);
    chip(s, 9.4, y + 0.22, tag, fg, bg);
    s.addText(h, {
      x: 9.4, y: y + 0.6, w: 2.8, h: 0.28,
      fontFace: F, fontSize: 13, bold: true, color: INK, isTextBox: true, margin: 0,
    });
    s.addText(d, {
      x: 9.4, y: y + 0.87, w: 2.83, h: 0.26,
      fontFace: F, fontSize: 10.5, color: MUTE, isTextBox: true, margin: 0,
    });
    y += 1.3;
  });

  card(s, 9.1, 5.88, 3.33, 1.08, BLUE_SOFT);
  body(s, 9.4, 5.88, 2.8, 1.08, [
    { text: "확인 못 한 것은", options: { size: 12, breakLine: true } },
    { text: "“이상 없음”이 아니라\n“모른다”", options: { bold: true, color: INK, size: 14 } },
  ], { valign: "middle", lineSpacing: 19 });
  chrome(s);
}

// ══════════════════════════════════════════════════ 08 다른 저장소
{
  const s = slide();
  kicker(s, "다른 저장소");
  title(s, [
    { text: "한 핀에 " },
    { text: "데이터선 두 개", options: { color: CRIT } },
    { text: "가 물려 있었습니다." },
  ], { h: 0.9 });

  card(s, 0.9, 2.15, 11.53, 2.3);
  mono(s, 1.25, 2.5, 10.83, 1.6, [
    { text: "U3.15 (I/O5) → /D5", options: { bold: true, color: INK, breakLine: true } },
    { text: "U3.15 (I/O7) → /D7", options: { bold: true, color: CRIT } },
  ], { size: 15, lineSpacing: 30 });

  body(s, 0.9, 4.75, 11.53, 0.5,
    "Alireza2317/EEPROM_programmer · CC0", { size: 12, color: MUTE });

  card(s, 0.9, 5.35, 11.53, 1.35, BLUE_SOFT);
  body(s, 1.3, 5.35, 10.73, 1.35, [
    { text: "AI 가 후보로 올리고, 저희 코드가 확인했습니다. ", options: { bold: true, color: INK, size: 15 } },
    { text: "저희 규칙 어느 것도 그 모양을 안 보고 있었는데, 열어 보니 사실이라 규칙으로 넣었습니다.", options: { size: 14 } },
  ], { valign: "middle", lineSpacing: 21 });
  chrome(s);
}

// ══════════════════════════════════════════════════ 10 LLM 대조
{
  const s = slide();
  kicker(s, "궁금해서 실제로 재봤습니다");
  title(s, [
    { text: "모델은 경고를 세 배 냈습니다.", options: { breakLine: true } },
    { text: "그중 열 건은 “확인할 수 없다”였습니다.", options: { color: BLUE } },
  ]);

  const cols = [
    ["", "대형 모델", "Prefab"],
    ["읽어낸 보드", "22 / 28", "28 / 28"],
    ["낸 경고", "44건", "16건"],
    ["근거를 끝까지 댐", "34 / 44", "16 / 16"],
  ];
  card(s, 0.9, 2.4, 7.5, 2.75);
  cols.forEach((row, r) => {
    const y = 2.62 + r * 0.63;
    const head = r === 0;
    s.addText(row[0], {
      x: 1.25, y, w: 3.0, h: 0.4,
      fontFace: F, fontSize: head ? 11.5 : 13, bold: !head, color: head ? MUTE : SUB,
      isTextBox: true, margin: 0, valign: "middle",
    });
    s.addText(row[1], {
      x: 4.5, y, w: 1.75, h: 0.4, align: "center",
      fontFace: F, fontSize: head ? 11.5 : 14, bold: true, color: head ? MUTE : MUTE,
      isTextBox: true, margin: 0, valign: "middle",
    });
    s.addText(row[2], {
      x: 6.4, y, w: 1.75, h: 0.4, align: "center",
      fontFace: F, fontSize: head ? 11.5 : 14, bold: true, color: head ? BLUE : INK,
      isTextBox: true, margin: 0, valign: "middle",
    });
  });

  card(s, 8.7, 2.4, 3.73, 2.75, CRIT_SOFT);
  body(s, 9.05, 2.4, 3.03, 2.75, [
    { text: "10 / 44", options: { size: 30, bold: true, color: CRIT, breakLine: true } },
    { text: "경고 안에 “확인할 수 없다”가 들어 있던 것.\n", options: { size: 12, breakLine: true } },
    { text: "받아 든 사람이 다시 확인해야 하면 도구가 아니라 숙제입니다.", options: { size: 12, bold: true, color: INK } },
  ], { valign: "middle", lineSpacing: 18 });

  card(s, 0.9, 5.4, 11.53, 1.3, BLUE_SOFT);
  body(s, 1.3, 5.4, 10.73, 1.3, [
    { text: "저희가 파는 건 “AI보다 똑똑하다”가 아니라 ", options: { size: 15 } },
    { text: "“같은 파일이면 언제나 같은 답”", options: { size: 15, bold: true, color: INK } },
    { text: "입니다.", options: { size: 15, breakLine: true } },
    { text: "판정하는 코드는 모델을 부르지 않습니다. 회로도가 저희 서버 밖으로 나가지 않는 이유도 그것입니다.", options: { size: 12.5 } },
  ], { valign: "middle", lineSpacing: 21 });
  chrome(s);
}

// ══════════════════════════════════════════════════ 11 고객
{
  const s = slide();
  kicker(s, "누가 쓰나");
  title(s, [
    { text: "공통점은 " },
    { text: "검토해 줄 사람이 없다", options: { color: BLUE } },
    { text: "는 것" },
  ], { h: 0.9 });

  const who = [
    ["하드웨어 스타트업", "발주 한 번이 런웨이를 깎습니다"],
    ["대학 연구실", "회로 담당이 대학원생 한 명입니다"],
    ["중소 제조업 R&D팀", "검토 인력을 따로 두기 어렵습니다"],
  ];
  who.forEach(([h, d], i) => {
    const x = 0.9 + i * 3.93;
    card(s, x, 2.2, 3.67, 2.6);
    s.addText(String(i + 1).padStart(2, "0"), {
      x: x + 0.4, y: 2.5, w: 1.0, h: 0.36,
      fontFace: MONO, fontSize: 14, bold: true, color: BLUE, isTextBox: true, margin: 0,
    });
    s.addText(h, {
      x: x + 0.4, y: 3.0, w: 2.9, h: 0.7,
      fontFace: F, fontSize: 18, bold: true, color: INK, isTextBox: true, margin: 0, lineSpacing: 25,
    });
    body(s, x + 0.4, 3.85, 2.9, 0.7, d, { size: 12.5, lineSpacing: 18 });
  });

  card(s, 0.9, 5.15, 11.53, 1.35, BLUE_SOFT);
  body(s, 1.3, 5.15, 10.73, 1.35, [
    { text: "대기업에는 회로도를 검토하는 사람이 따로 있습니다. ", options: { size: 15 } },
    { text: "이 셋에는 없습니다.", options: { size: 15, bold: true, color: INK } },
  ], { valign: "middle" });
  chrome(s);
}

// ══════════════════════════════════════════════════ 12 요금제
{
  const s = slide();
  kicker(s, "수익 구조");
  title(s, [
    { text: "한 번만 막아도 " },
    { text: "몇 년치가 회수", options: { color: BLUE } },
    { text: "됩니다" },
  ], { h: 0.9 });

  const plans = [
    ["무료", "학생 · 개인", ["검사 무제한", "결과를 링크로 공유", "판정마다 근거와 출처"], false],
    ["Pro", "1인 개발자 · 소규모 팀", ["무료의 모든 것", "비공개 링크", "검사 기록 보관"], false],
    ["Team", "회사", ["Pro의 모든 것", "팀 단위 계정", "CI 연동 · 머지 차단"], true],
  ];
  plans.forEach(([name, who, lines, hi], i) => {
    const x = 0.9 + i * 3.93;
    card(s, x, 2.15, 3.67, 2.95, hi ? BLUE_SOFT : CARD);
    s.addText(name, {
      x: x + 0.4, y: 2.45, w: 2.9, h: 0.4,
      fontFace: F, fontSize: 20, bold: true, color: hi ? BLUE : INK, isTextBox: true, margin: 0,
    });
    s.addText(who, {
      x: x + 0.4, y: 2.87, w: 2.9, h: 0.3,
      fontFace: F, fontSize: 11.5, color: MUTE, isTextBox: true, margin: 0,
    });
    const runs = [];
    lines.forEach((l, k) => {
      runs.push({ text: (k ? "\n" : "") + "· " + l, options: {} });
    });
    body(s, x + 0.4, 3.35, 2.9, 1.5, runs, { size: 12.5, lineSpacing: 22 });
  });

  card(s, 0.9, 5.4, 11.53, 1.3, CARD);
  body(s, 1.3, 5.4, 10.73, 1.3, [
    { text: "무료로도 검사는 무제한입니다. ", options: { size: 15, bold: true, color: INK } },
    { text: "판정 원가가 실제로 0에 가깝기 때문입니다 — 판정은 순수한 코드라 AI도 네트워크도 쓰지 않습니다.", options: { size: 13.5, breakLine: true } },
    { text: "재작업 한 번이 수천만원인데, 구독료는 그 백분의 일 수준입니다.", options: { size: 13.5 } },
  ], { valign: "middle", lineSpacing: 21 });
  chrome(s);
}

// ══════════════════════════════════════════════════ 13 시장 확장
//
// **앞판은 「기술이 어떻게 커지나」였다.** 칩·부품·배포 자리 셋을 늘어놨는데,
// 심사 기준의 「확장성」은 그걸 묻는 게 아니라 **누구에게 더 팔리는가**를 묻는다.
//
// 그래서 축을 고객으로 바꾼다 — 개인 → 회사 팀 → 공공·교육.
// 기술 이야기는 사라지지 않고 **아래 띠에서 「그래서 원가가 안 는다」의 근거**가 된다.
{
  const s = slide();
  kicker(s, "시장 확장");
  title(s, [
    { text: "같은 제품으로 " },
    { text: "고객만 넓힙니다", options: { color: BLUE } },
  ], { h: 0.9 });

  const lanes = [
    ["지금", "B2C", "개인 · 소규모 팀", OK, OK_SOFT,
     ["웹 검사 무제한 · 무료", "Pro 9,900원 / 월", "학생 · 1인 개발자"]],
    ["다음", "B2B", "회사 개발팀", BLUE, BLUE_SOFT,
     ["CI 연동 · 머지 차단", "Team 39,000원 / 월", "한 번 붙으면 안 걷어냅니다"]],
    ["그다음", "B2G", "공공 · 교육", WARN, WARN_SOFT,
     ["시제품 지원 기관", "대학 실습 · 캡스톤", "기관 단위 계약"]],
  ];

  lanes.forEach(([when, tag, who, fg, bg, items], i) => {
    const x = 0.9 + i * 3.93;
    card(s, x, 2.05, 3.67, 2.55, CARD);
    chip(s, x + 0.4, 2.32, when, fg, bg);
    s.addText(tag, {
      x: x + 0.4, y: 2.78, w: 2.9, h: 0.46,
      fontFace: F, fontSize: 26, bold: true, color: fg, isTextBox: true, margin: 0,
    });
    s.addText(who, {
      x: x + 0.4, y: 3.22, w: 2.9, h: 0.3,
      fontFace: F, fontSize: 13, bold: true, color: INK, isTextBox: true, margin: 0,
    });
    body(s, x + 0.4, 3.58, 2.9, 0.95,
      items.map((t, k) => ({
        text: "· " + t,
        options: { size: 11.5, breakLine: k < items.length - 1 },
      })),
      { lineSpacing: 17 });
  });

  // **B2G 가 왜 진짜인가.** 4장에서 이미 깐 근거를 여기서 돈으로 잇는다.
  card(s, 0.9, 4.8, 11.53, 1.15, SUNK);
  body(s, 1.3, 4.8, 10.73, 1.15, [
    { text: "세금으로 시제품을 만들어 주는 자리는 이미 있습니다 — ", options: { size: 13 } },
    { text: "서울시 한 곳에서만 2023년에 전자보드 34,000개", options: { size: 13, bold: true, color: INK } },
    { text: ".", options: { size: 13, breakLine: true } },
    { text: "만들어 주는 자리는 있는데, 틀린 걸 미리 잡아 주는 자리는 없습니다.", options: { size: 13, bold: true, color: INK } },
  ], { valign: "middle", lineSpacing: 20 });

  // 기술 이야기는 여기서 「원가가 안 는다」의 근거로만 남는다
  card(s, 0.9, 6.1, 11.53, 0.92, BLUE_SOFT);
  const proof = [
    ["0", "개", "규칙 코드 안의 핀 번호"],
    ["0", "회", "검사가 부르는 AI"],
    ["1", "번", "부품당 데이터시트 읽기"],
  ];
  proof.forEach(([v, u, label], i) => {
    const x = 1.3 + i * 3.6;
    s.addText(
      [
        { text: v, options: { fontSize: 22, bold: true, color: BLUE } },
        { text: u + "  ", options: { fontSize: 12, bold: true, color: BLUE } },
        { text: label, options: { fontSize: 12, color: SUB } },
      ],
      { x, y: 6.1, w: 3.5, h: 0.92, valign: "middle", fontFace: F, isTextBox: true, margin: 0 }
    );
  });
  chrome(s);
}

// ══════════════════════════════════════════════════ 14 CI
{
  const s = slide();
  kicker(s, "제품의 최종 형태");
  title(s, [
    { text: "회로도는 계속 바뀝니다.", options: { breakLine: true } },
    { text: "그래서 검사도 계속 돌아야 합니다.", options: { color: BLUE } },
  ]);

  const steps = ["코드 수정", "PR", "자동 검사", "어긋나면 빨간불"];
  steps.forEach((t, i) => {
    const x = 0.9 + i * 3.0;
    const last = i === steps.length - 1;
    card(s, x, 2.5, 2.6, 1.0, last ? CRIT_SOFT : CARD);
    s.addText(t, {
      x, y: 2.5, w: 2.6, h: 1.0, align: "center", valign: "middle",
      fontFace: F, fontSize: 15, bold: true, color: last ? CRIT : INK, isTextBox: true, margin: 0,
    });
    if (!last) {
      s.addText("→", {
        x: x + 2.6, y: 2.5, w: 0.4, h: 1.0, align: "center", valign: "middle",
        fontFace: F, fontSize: 16, bold: true, color: MUTE, isTextBox: true, margin: 0,
      });
    }
  });

  mono(s, 0.9, 3.85, 11.53, 1.5, [
    { text: "- uses: ", options: { color: MUTE } },
    { text: "PNU-2026-AI-Hackathon/pnuai-c-06-EECE/.github/actions/prefab-check@main", options: { bold: true, color: INK, breakLine: true } },
    { text: "  with:", options: { color: MUTE, breakLine: true } },
    { text: "    netlist: hardware/board.net.xml\n    firmware: firmware/", options: { color: INK } },
  ], { size: 11.5, lineSpacing: 19 });

  body(s, 0.9, 5.6, 11.53, 1.0, [
    { text: "개발팀이 이미 쓰는 자리에 그대로 들어갑니다. ", options: { size: 15, bold: true, color: INK } },
    { text: "이미 저희 저장소에서 돌고 있습니다 (.github/workflows/drift.yml).", options: { size: 13.5, breakLine: true } },
    { text: "한 번 붙으면 잘 걷어내지 않습니다 — 팀 단위 구독이 여기서 나옵니다.", options: { size: 13.5 } },
  ], { lineSpacing: 21 });
  chrome(s);
}

// ══════════════════════════════════════════════════ 15 머지 차단  ★
//
// **다시 그린 그림을 진짜 캡처로 바꿨다 (8/27).**
//
// 앞판은 GitHub 머지 상자를 우리 토큰으로 다시 그렸다. 이유는 「스크린샷은
// 뒷자리에서 안 읽힌다」였고 그건 맞는 걱정이었다. 그래서 **캡처를 쓰되 머지
// 상자만 잘라 크게 쓴다** — 읽힘 문제를 없애면서 「진짜」를 얻는다.
//
// 이제 「다시 그린 것입니다」 각주가 필요 없다. 진짜니까.
{
  const s = slide();
  kicker(s, "그리고 여기서 끝나지 않습니다");
  title(s, [
    { text: "빨간불에서 멈추지 않고, " },
    { text: "머지 자체가 막힙니다.", options: { color: CRIT } },
  ], { h: 0.9 });

  // 4.34 : 1 — 잘라낸 비율 그대로 넣는다
  const IW = 11.2, IH = IW / 4.34;
  s.addImage({ path: "merge-box.png", x: (W - IW) / 2, y: 2.15, w: IW, h: IH, shadow: soft() });

  // 무엇을 봐야 하는지 짚어 준다. 화면에 처음 온 사람은 어디를 볼지 모른다.
  const marks = [
    ["필수 검사가 실패", CRIT, CRIT_SOFT],
    ["Required 표시", CRIT, CRIT_SOFT],
    ["머지 버튼이 회색", INK, SUNK],
  ];
  marks.forEach(([t, fg, bg], i) => {
    chip(s, 1.05 + i * 3.9, 2.15 + IH + 0.28, t, fg, bg);
  });

  card(s, 0.9, 2.15 + IH + 0.95, 11.53, 1.15, BLUE_SOFT);
  body(s, 1.3, 2.15 + IH + 0.95, 10.73, 1.15, [
    { text: "저희 저장소 main 에 실제로 걸어 둔 규칙입니다. ", options: { size: 14, bold: true, color: INK } },
    { text: "회로도 대조 검사가 통과하지 않으면 버튼이 눌리지 않습니다 — 저장소 주인도 못 넘깁니다.", options: { size: 14, breakLine: true } },
    { text: "사람이 검토를 깜빡해도 막힙니다. 이게 저희가 팀 단위로 파는 이유입니다.", options: { size: 13.5, color: SUB } },
  ], { valign: "middle", lineSpacing: 20 });

  body(s, 0.9, H - 1.0, 11.53, 0.4, [
    { text: "prefab-web.onrender.com", options: { size: 12, bold: true, color: BLUE } },
    { text: "          팀 전전컴 · 박강현 조우진 유동훈 한지양 권지효", options: { size: 12, color: MUTE } },
  ]);
  chrome(s);
}

const NOTES = [
  `[표지 · 25초]
안녕하세요. 창업트랙 C-06 팀 전전컴입니다.
저희는 보드를 발주하기 전에, 코드와 회로도가 어긋난 곳을 찾는 도구를 만들었습니다.
한 장면부터 보여드리겠습니다.`,
  `[어긋난 코드 · 40초]
공개 저장소에서 저희 도구가 실제로 찾은 것입니다.
납땜을 바꾸면서 백라이트 핀을 19번으로 옮겨 놨는데, 다른 파일의 상수는 25번에 그대로 남아 있습니다.
그리고 25번은 이제 디스플레이 데이터선입니다.
아직 아무도 그 상수를 안 써서 안 터졌을 뿐이고, 같은 파일에 적혀 있는 기능이 켜지는 순간 데이터선에 신호가 걸립니다.
컴파일도 되고 업로드도 됩니다. 어느 검사에도 안 걸립니다.`,
  `[비용 · 40초]
소프트웨어는 잘못돼도 다시 배포하면 됩니다. 하드웨어는 돈이 사라집니다.
설계 프로젝트 조사를 보면 평균 2.9회를 다시 만들고, 한 번에 약 6천만원, 8.5일이 듭니다.
저희가 줄이려는 게 이 숫자입니다.`,
  `[시장 근거 · 35초]
저희만 그렇게 보는 게 아닙니다. 서울시가 이 문제에 세금을 쓰고 있습니다.
시제품 제작을 지원하는 이유로 "위험부담이 커서 진입장벽이 크다"를 듭니다.
그런데 지원은 만들어 주는 것이지, 틀린 걸 미리 잡아 주지는 않습니다.`,
  `[빈자리 · 30초]
지금 도구들이 보는 곳을 그려 봤습니다.
회로도 검사 도구는 코드를 안 읽고, 코드 정적 분석은 회로도를 모릅니다.
그 사이는 아무도 안 봅니다. 지금은 사람이 기억으로 잇고 있습니다.`,
  `[한 문장 · 20초]
저희가 하는 일은 한 문장입니다.
이미 짜 놓은 펌웨어가, 바뀐 회로도를 따라가고 있는지 검사합니다.
회로도와 펌웨어와 데이터시트, 셋을 나란히 놓고 대조합니다.`,
  `[발견 카드 · 45초]
2장에서 보신 그 저장소를 그대로 넣은 결과입니다.
판정 하나에 근거가 세 줄 붙습니다. 회로도가 아는 것, 코드가 아는 것, 부품이 아는 것.
코드는 파일 이름과 줄 번호까지 나옵니다.
그리고 맨 아래를 봐 주세요. 부품 정보는 "모름"이라고 적혀 있습니다.
확인 못 한 것을 "이상 없음"이라고 하지 않습니다. 이게 저희가 제일 신경 쓴 부분입니다.`,
  `[다른 저장소 · 35초]
다른 저장소에서 찾은 것입니다. 한 핀에 데이터선 두 개가 물려 있습니다.
이건 AI 가 후보로 올리고 저희 코드가 확인해서 규칙이 된 겁니다.
저희 규칙 어느 것도 그 모양을 안 보고 있었는데, 열어 보니 사실이라 규칙으로 만들어 넣었습니다.
AI 는 제안하고, 판정은 코드가 합니다. 다음 장이 그 이유입니다.`,
  
  `[LLM 대조 · 55초]
가장 많이 받는 질문입니다. 그냥 AI에 물어보면 안 되냐.
궁금해서 실제로 재봤습니다. 같은 보드 28개를 대형 모델과 나란히 돌렸습니다.
모델은 6개를 통째로 건너뛰었습니다. 입력이 커서요. 안 본 보드는 문제 없는 보드가 아니라 모르는 보드입니다.
경고는 세 배 가까이 많이 냈는데, 그중 10건은 경고 안에 "확인할 수 없다"가 들어 있었습니다.
받아 든 사람이 다시 확인해야 하면 도구가 아니라 숙제입니다.
저희가 파는 건 "AI보다 똑똑하다"가 아니라 "같은 파일이면 언제나 같은 답"입니다.
그리고 저희는 오탐도 쟀습니다. 한 번도 안 써 본 보드 38개에서 1건입니다. 재본 팀이 저희밖에 없습니다.`,
  `[고객 · 30초]
저희 고객 셋입니다. 하드웨어 스타트업, 대학 연구실, 중소 제조업 R&D팀.
공통점은 회로도를 검토해 줄 사람이 없다는 것입니다.
대기업에는 그 사람이 따로 있습니다. 이 셋에는 없습니다.`,
  `[요금 · 40초]
무료로도 검사는 무제한입니다. 판정 원가가 실제로 0에 가깝기 때문입니다 —
판정은 순수한 코드라 AI도 네트워크도 쓰지 않습니다.
돈은 팀으로 쓸 때 받습니다. 재작업 한 번이 수천만원인데 구독료는 그 백분의 일입니다.
한 번만 막아도 몇 년치가 회수됩니다.`,
  `[시장 확장 · 50초]
같은 제품으로 고객만 넓힙니다.
지금은 개인과 소규모 팀입니다. 웹 검사는 무제한 무료입니다.
다음은 회사 개발팀입니다. CI에 붙이면 머지가 막히고, 한 번 붙은 검사는 잘 걷어내지 않습니다.
그다음이 공공과 교육입니다. 4장 기억하시죠. 세금으로 시제품을 만들어 주는 자리는 이미 있습니다.
서울시 한 곳에서만 작년에 전자보드 삼만 사천 개를 만들어 줬습니다.
만들어 주는 자리는 있는데, 틀린 걸 미리 잡아 주는 자리가 없습니다. 저희가 그 자리입니다.
그리고 넓혀도 원가가 안 늡니다. 아래 숫자 셋이 그 이유입니다.`,
  
  `[CI · 35초]
지금까지 보여드린 건 파일을 올려 한 번 검사하는 모습입니다.
하지만 회로도는 계속 바뀝니다. 그래서 검사도 계속 돌아야 합니다.
최종 형태는 코드를 고칠 때마다 자동으로 도는 검사입니다.
개발팀이 이미 쓰는 자리에 그대로 들어갑니다.`,
  `[머지 차단 · 45초]
그리고 빨간불에서 끝나지 않습니다.
이건 저희 저장소의 실제 화면입니다. 회로도를 예전 상태로 되돌린 PR을 하나 올려 뒀습니다.
회로도 대조 검사가 실패했고, 오른쪽에 Required라고 붙어 있습니다.
아래 머지 버튼을 봐 주세요. 회색입니다. 눌리지 않습니다.
어긋난 회로도는 저장소에 들어갈 수 없습니다.
사람이 검토를 깜빡해도 막힙니다 — 이게 저희가 팀 단위로 파는 이유입니다.
지금 열려 있습니다. 감사합니다.`,
];

if (NOTES.length !== DECK.length) {
  throw new Error(`노트 ${NOTES.length}개 · 슬라이드 ${DECK.length}장 — 어긋났다`);
}
DECK.forEach((s, i) => s.addNotes(NOTES[i]));

pres.writeFile({ fileName: "창업-06-전전컴_최종.pptx" }).then((f) =>
  console.log("  만들어짐:", f)
);
