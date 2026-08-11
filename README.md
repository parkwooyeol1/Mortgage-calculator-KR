# 저당액 계산기 (Mortgage Calculator KR)

채권최고액을 기준으로 대출원금과 현재 저당액(기입값)을 추정하는 한국형 저당액 계산 GUI 프로그램입니다.

## 계산 규칙

- **대부 / 개인**: 대출원금 = 채권최고액 ÷ 150 × 100 → 기간 계산 없이 그대로 저당액으로 사용
- **은행**: 대출원금 = 채권최고액 ÷ 120 × 100
  - 접수일자부터 오늘까지 경과가 1개월 미만이면 → 원금을 그대로 저당액으로 사용
  - 1개월 이상이면 → 20년(240개월) / 연 3% 원리금균등상환 기준으로 경과 개월만큼 상환한 잔액을 저당액으로 사용

## 실행 방법

Python 3와 표준 라이브러리(tkinter)만 있으면 됩니다.

```bash
python mortgage_gui.py
```

## 실행 파일 빌드

`.spec` 파일과 [PyInstaller](https://pyinstaller.org/)를 사용해 단일 실행 파일(.exe)을 만들 수 있습니다.

```bash
pip install pyinstaller
pyinstaller 저당액계산기v3.spec
```

빌드 결과물(`dist/`, `build/`, `*.exe`)은 저장소에 포함하지 않습니다.
