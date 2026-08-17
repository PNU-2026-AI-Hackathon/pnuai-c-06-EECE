---
name: prefab-datasheet
description: Prefab 프로젝트에서 부품 데이터시트로부터 전기적 사실(fact)을 추출하고 부품 사실 DB에 저장할 때 사용한다. MPN으로 데이터시트를 찾고, PDF에서 정격 값을 읽고, 출처가 붙은 JSON으로 정규화한다. "데이터시트 읽어줘", "이 부품 전압 확인", "MPN 조회", "fact 추출", "부품 DB에 넣어줘", "Voh 찾아줘", "이 경고 해제할 수 있는지 확인" 같은 요청에 사용.
---

# 부품 데이터시트 사실 추출

이 파이프라인이 Prefab의 유일한 해자다. **추출한 사실은 부품당 한 번만 만들면 전 사용자가 재사용한다.**
DB가 쌓일수록 오탐이 줄고 한계비용이 0에 수렴한다. 그러니 **정확도가 속도보다 항상 우선이다.**

## 절대 원칙

> **모르면 `null`을 반환한다. 추정값을 넣지 않는다.**

틀린 fact 하나는 그 부품을 쓰는 모든 사용자에게 오탐 또는 미검출을 만든다.
"아마 3.3V일 것"은 DB에 들어가면 안 되는 값이다.

## 절차

### 1단계 — 캐시부터 본다

```sql
SELECT * FROM part_facts WHERE mpn = ? AND field = ?;
```

있으면 **끝이다. LLM을 호출하지 않는다.** 이게 단위경제의 핵심이다.
캐시 적중 여부를 로그에 남긴다 (발표에서 쓸 지표).

### 2단계 — MPN을 정규화한다

BOM의 부품번호는 지저분하다. 접미사·패키지·수량 표기를 정리한다.

```
"HLK-LD2410C  (5V)"  → "HLK-LD2410C"
"ESP32-C6-WROOM-1-N8" → "ESP32-C6-WROOM-1"   (메모리 옵션 분리)
```

정규화에 실패하면 **원문 그대로 두고 `confidence: low`로 표시**한다. 억지로 맞추지 않는다.

### 3단계 — 데이터시트를 찾는다

우선순위대로 시도하고, **어디서 받았는지 URL을 반드시 기록**한다.

1. 제조사 공식 도메인
2. 주요 유통사 (Digi-Key, Mouser, LCSC)
3. 그 외

공식 출처를 못 찾으면 `source_tier: unofficial`로 표시한다. 규칙 엔진이 이 등급을 보고
판정을 `UNRESOLVED`로 낮출 수 있어야 한다.

### 4단계 — 표를 찾는다

값이 사는 위치는 정해져 있다. 순서대로 뒤진다.

| 찾는 값 | 보통 있는 표 |
|---|---|
| 절대 최대 입력 전압 | **Absolute Maximum Ratings** |
| 동작 전압 범위 | Recommended Operating Conditions |
| 출력 High 전압 (Voh) | **Electrical Characteristics** / DC Characteristics |
| 입력 문턱 (Vih/Vil) | Electrical Characteristics |
| 필요 외부 소자 | Application Circuit / Typical Application |

**Absolute Maximum과 Recommended Operating을 혼동하지 않는다.** 전자는 "이걸 넘으면 파손",
후자는 "이 범위에서 정상 동작". 판정 기준이 다르다. 어느 표에서 읽었는지 반드시 기록한다.

### 5단계 — JSON 스키마로 강제 출력한다

자유 텍스트로 받지 않는다. 아래 스키마를 강제한다.

```json
{
  "mpn": "HLK-LD2410C",
  "facts": [
    {
      "field": "voh_max",
      "value": 3.3,
      "unit": "V",
      "table": "Electrical Characteristics",
      "page": 3,
      "quote": "OUT high level output voltage 3.3V",
      "confidence": "high"
    },
    {
      "field": "vcc_nominal",
      "value": 5.0,
      "unit": "V",
      "table": "Recommended Operating Conditions",
      "page": 2,
      "quote": "Supply voltage 5V DC",
      "confidence": "high"
    },
    {
      "field": "output_type",
      "value": null,
      "unit": null,
      "table": null,
      "page": null,
      "quote": null,
      "confidence": "none",
      "reason": "push-pull인지 open-drain인지 데이터시트에 명시되지 않음"
    }
  ],
  "source_url": "https://...",
  "source_tier": "official"
}
```

- `quote`는 **PDF 원문 그대로**. 번역하거나 요약하지 않는다.
- `page`가 없는 fact는 DB에 넣지 않는다. 출처 없는 값은 값이 아니다.
- 값이 없으면 `value: null` + `reason`. 이건 실패가 아니라 **정상적인 결과**다.

### 6단계 — DB에 쓰고 영향을 보고한다

저장한 뒤, 이 fact가 **기존 경고를 해제하는지** 확인해서 알린다.

```
HLK-LD2410C 등록 완료 (fact 4건, 출처: 제조사 공식 p.2-3)
  → PRESENCE_3V3의 R12 경고가 해제됩니다.
     OUT은 5V 전원에서도 3.3V 레벨 출력 (p.3 Electrical Characteristics)
  → 부품 DB: 12 → 13
```

이 "플래그가 지워지는 순간"이 제품의 핵심 경험이다. 반드시 사용자에게 보여준다.

## 자주 나오는 함정

- **모듈 vs 칩**: `ESP32-C6`(칩)과 `ESP32-C6-WROOM-1`(모듈)은 다른 문서다. 핀 번호 체계도 다르다.
- **개발보드 실크 이름**: `D7`, `D8` 같은 이름은 칩 GPIO 번호가 아니다. **모듈 핀아웃 DB로 변환**해야 한다.
- **범용 모듈**: "5V 릴레이 모듈" 같은 부품은 제조사가 불명확한 경우가 많다.
  → **추측하지 말고 `UNRESOLVED`로 두고, 사용자에게 모델명을 묻는다.**
- **옵토커플러 유무**: 릴레이 모듈은 절연형/비절연형에 따라 판정이 정반대다. 확인 못 하면 판정하지 않는다.

## 하지 말 것

- 웹 검색 결과 요약문에서 값을 가져오는 것 (**반드시 PDF 본문**)
- 유사 부품의 값을 유추해서 채우는 것
- `confidence: low`인 값으로 `PASS` 판정을 내는 것
- 같은 MPN을 두 번 조회하는 것 (캐시를 먼저 봤는지 확인)
