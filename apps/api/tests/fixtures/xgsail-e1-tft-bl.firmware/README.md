# 출처

`FForzano/xgsail-e1` — **Apache License 2.0**
https://github.com/FForzano/xgsail-e1

아래 세 파일은 그 저장소에서 **결함과 관련된 줄만** 발췌한 것입니다.
원 저작자의 주석을 지우지 않았습니다 — 그 주석이 이 케이스의 핵심 근거입니다.

## 이 케이스가 무엇인가

배선이 바뀌어 백라이트가 GPIO19 로 옮겨갔습니다. 개발자가 `User_Setup.h` 는
고치면서 주석까지 남겼는데 **`config.h` 가 안 따라왔습니다.**
그 결과 코드가 GPIO25 에 PWM 을 붙이는데, 회로도상 GPIO25 는 SPI MISO 입니다.

**라벨 없는 남의 실제 프로젝트에서 나온 결함입니다.** 우리가 만든 상황이 아닙니다.
LLM baseline 이 먼저 지적했고 코드로 확인했습니다 (`_docs/규모_실험.md`).
