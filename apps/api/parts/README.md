# 부품 사실 파일

사람이 데이터시트를 읽고 손으로 적는 자리다. **LLM 없이도 DB 를 채울 수 있다.**

```bash
python -m prefab --facts-load parts/hlk-ld2410c.json
python -m prefab --facts
```

`_TEMPLATE.json` 을 복사해서 쓴다. 파일 이름은 부품번호를 소문자로.

LLM 으로 초안을 뽑을 수도 있다 (`ANTHROPIC_API_KEY` 필요):

```bash
python -m prefab --extract ld2410c.pdf --mpn HLK-LD2410C \
    --source-url https://... --source-tier official --pages 15-19 \
    > parts/hlk-ld2410c.json
```

**결과가 DB 로 바로 안 들어간다.** 파일로 나오고, 사람이 보고 커밋할지 정한다.
그리고 **모델이 댄 인용문이 그 쪽 원문에 없으면 그 항목은 자동으로 빠진다** —
지어낸 출처는 여기서 걸린다.
서식 자체는 `mpn` 이 비어 있어서 그대로 넣으면 통째로 거절된다 — 실수로 DB 를 더럽히지 않는다.

## 절대 원칙

> **모르면 `value: null` + `reason` 을 쓴다. 추정값을 넣지 않는다.**

틀린 사실 하나는 그 부품을 쓰는 **모든 사용자**에게 오탐 또는 미검출을 만든다.
"아마 3.3V일 것"은 여기 들어가면 안 되는 값이다.

## 저장기가 거절하는 것

`--facts-load` 는 아래를 **받아들이지 않고 화면에 이유를 찍는다.**

| 거절 | 왜 |
|---|---|
| 값이 있는데 `page` 나 `quote` 가 없다 | 출처 없는 값은 값이 아니다 |
| 값이 없는데 `reason` 이 없다 | "모른다"는 왜 모르는지까지 말해야 한다 |
| `mpn` 이 비었다 | 어느 부품 얘기인지 모른다 |

`value: null` 자체는 거절 사유가 **아니다.** 찾아봤지만 없더라는 것도 사실이고,
저장해 둬야 같은 부품을 두 번 조회하지 않는다.

## 보드가 칩을 얹었을 때

BOM 에는 보드 이름(`XIAO-ESP32C6`)이 적히는데 데이터시트는 칩 이름(`ESP32-C6`)으로 나온다.
칩 사실 파일에 어느 보드가 그 칩을 쓰는지 적으면 이어진다.

```json
{ "mpn": "ESP32-C6", "applies_to_boards": ["XIAO-ESP32C6"], "facts": [...] }
```

**핀 전기 특성만 물려받는다.** `vcc_nominal` 은 안 넘어간다 — 보드에는 레귤레이터가 있다
(XIAO 는 USB 5V 를 받아 칩에 3.3V 를 준다). 칩 전압을 보드 전압이라고 하면 틀린 값이다.
보드 자체 데이터시트에 값이 있으면 그게 칩 값보다 세다.

## 항목 이름

`src/prefab/datasheet/facts.py` 에 상수로 있다. 여기 없는 이름을 지어내면
규칙이 영영 못 찾는다.

| 이름 | 뜻 | 보통 있는 표 |
|---|---|---|
| `vin_absolute_max` | 넘으면 **파손**되는 입력 전압 | Absolute Maximum Ratings |
| `vcc_nominal` | 정격 공급 전압 | Recommended Operating Conditions |
| `voh_max` · `vol_max` | 출력 High/Low 전압 | Electrical Characteristics |
| `vih_min` · `vil_max` | 입력 문턱 | Electrical Characteristics |
| `output_type` | `push-pull` / `open-drain` | Electrical Characteristics |
| `io_level` | 모듈 IO 가 도는 로직 레벨 | Interface / 사양 표 |
| `input_pullup_to` | 입력 핀이 내부에서 어디로 풀업되는가 | Application Circuit |

**`voh_max` 와 `io_level` 을 섞지 않는다.** `voh_max` 는 min/max 열이 있는 출력 규격이고,
`io_level` 은 "IO level 3.3V" 같은 로직 레벨 표기다. 모듈 데이터시트는 Voh 규격을 잘 안 준다.
없는 규격을 `voh_max` 에 적으면 그건 지어낸 값이다 — 실제로 한 번 그렇게 적었다가
LLM 추출이 반박해서 항목을 나눴다. 규칙은 둘 다 본다 (`voh_max` 를 먼저).

**Absolute Maximum 과 Recommended Operating 을 섞지 않는다.** 전자는 "넘으면 파손",
후자는 "이 범위에서 정상 동작"이다. 판정 기준이 다르므로 어느 표에서 읽었는지 반드시 적는다.

## `confidence`

| 값 | 언제 |
|---|---|
| `high` | 표에서 그 값을 직접 읽었다 |
| `medium` | 표에 있지만 조건이 붙어 있다 (온도·부하 등) |
| `low` | 본문 서술에서 유추했다 — **이 값으로는 PASS 판정이 안 난다** |
| `none` | 값이 없다 |

## `source_tier`

`official`(제조사 공식) · `distributor`(Digi-Key·Mouser·LCSC) · `unofficial`(그 외).
공식이 아니면 규칙이 판정을 `UNRESOLVED` 로 낮출 수 있어야 하므로 정직하게 적는다.
