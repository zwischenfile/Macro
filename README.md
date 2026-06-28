# Macro GUI

PyQt5 기반의 Windows용 매크로 편집기입니다. 마우스, 키보드, 텍스트 입력, 대기, 날짜 입력, 화면 캡처 같은 동작을 JSON 프로필로 저장하고 즉시 실행하거나 예약 실행할 수 있습니다.

## 주요 기능

- `_Script` 폴더의 JSON 매크로 프로필 생성, 편집, 저장
- 클릭, 마우스 이동, 마우스 누름/떼기, 스크롤, 키 입력, 텍스트 입력, 대기 동작 지원
- 현재 마우스 위치 클릭, 단축키 반복 실행, 동적 날짜 입력 지원
- 일련번호 목록에서 한 줄씩 입력하거나 클립보드로 붙여넣고 사용 완료 목록으로 이동
- 화면 캡처 결과를 `_Script/Capture/`에 저장
- 입력 기록기로 실제 마우스/키보드 입력을 매크로 동작 목록에 반영
- 매크로 즉시 실행, 예약 실행, 실행 중 중지
- 동작 복사, 잘라내기, 붙여넣기, 삭제, 순서 이동
- 창 항상 위 표시 옵션

## 요구 사항

- Python 3.10 이상 권장
- Windows 환경 권장
- `requirements.txt`에 정의된 Python 패키지

전역 단축키와 입력 자동화 기능은 OS 권한, 보안 프로그램, 실행 중인 앱의 권한 수준에 영향을 받을 수 있습니다.

## 설치

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 실행

가상환경을 활성화한 상태에서 실행합니다.

```powershell
python MacroGUI.py
```

전역 Python 환경에 의존성을 설치했다면 다음처럼 실행할 수도 있습니다.

```powershell
py -3 MacroGUI.py
```

## 사용 흐름

1. 앱을 실행하면 `_Script` 폴더의 JSON 매크로가 목록에 표시됩니다.
2. 새 매크로를 만들거나 기존 매크로를 선택합니다.
3. `추가` 버튼으로 동작을 직접 입력하거나 `기록기 열기`로 실제 입력을 기록합니다.
4. 필요하면 일련번호 입력 영역에 사용할 값을 한 줄씩 넣습니다.
5. 매크로를 저장한 뒤 `즉시 실행` 또는 `예약 실행`을 사용합니다.

기본 즉시 실행 단축키는 `ctrl+1`, 기록기 중지 단축키는 `f8`입니다. 기본값은 `macro_gui/constants.py`에서 관리됩니다.

## 지원 동작

- `label`: 동작 목록을 구분하는 라벨
- `click`: 좌표 기반 단일/더블 클릭
- `move`: 지정 좌표로 마우스 이동
- `mouse_down`, `mouse_up`: 마우스 버튼 누름/떼기
- `scroll`: 가로/세로 스크롤
- `current_click`: 현재 위치 클릭 반복
- `type`: 텍스트 직접 입력
- `clipboard_paste`: 클립보드에 텍스트를 복사한 뒤 붙여넣기
- `keypress`: 단축키 또는 키 입력 반복
- `key_down`, `key_up`: 키 누름/떼기
- `dynamic_date`: 현재 날짜 기준 오프셋과 형식으로 날짜 입력
- `serial_input`: 일련번호 목록의 첫 줄을 직접 입력
- `serial_clipboard_copy`: 일련번호 목록의 첫 줄을 클립보드로 붙여넣기
- `capture`: 화면 캡처 저장
- `wait`: 지정 시간 대기

## 프로젝트 구조

```text
MacroGUI.py              # 애플리케이션 진입점
requirements.txt         # Python 패키지 의존성
README.md                # 프로젝트 문서
.gitignore               # Git 제외 규칙
macro_gui/
  app.py                 # QApplication 초기화
  main_window.py         # 메인 UI와 매크로 프로필 관리
  dialogs.py             # 동작 입력/편집 다이얼로그
  recorder.py            # 마우스/키보드 입력 기록기
  workers.py             # 매크로 실행 및 예약 작업
  utils.py               # 공통 유틸리티
  constants.py           # 동작 타입, 단축키, 기본값
  dependencies.py        # 선택 의존성 import 처리
_Script/
  *.json                 # 매크로 프로필 저장 위치
  Capture/               # 화면 캡처 저장 위치, Git 제외
```

## 주의 사항

- 좌표 기반 매크로는 화면 해상도, 배율, 창 위치가 바뀌면 다르게 동작할 수 있습니다.
- PyAutoGUI fail-safe가 활성화되어 있으므로 실행 중 마우스를 화면 모서리로 이동하면 자동화가 중단될 수 있습니다.
- `keyboard`, `pynput`, `pyautogui`는 일부 환경에서 관리자 권한이나 접근성 권한이 필요할 수 있습니다.
- `_Script/*.json`은 매크로 데이터이므로 필요한 파일만 커밋하고, 실행 중 생성되는 `_Script/Capture/` 이미지는 커밋하지 않습니다.
