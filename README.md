# Macro GUI

PyQt5 기반의 데스크톱 매크로 편집기입니다. 마우스/키보드 동작을 JSON 프로필로 저장하고, 즉시 실행하거나 예약 실행할 수 있습니다.

## 주요 기능

- JSON 매크로 프로필 생성, 수정, 저장
- 클릭, 스크롤, 키 입력, 텍스트 입력, 대기, 날짜 입력, 화면 캡처 액션 지원
- 매크로 기록기로 실제 마우스/키보드 입력을 액션 목록에 반영
- 일련번호 목록을 순차적으로 입력하거나 클립보드로 붙여넣기
- 예약 실행 및 전역 단축키 실행
- 실행 중 중지, 액션 복사/잘라내기/붙여넣기, 순서 이동

## 요구 사항

- Python 3.10 이상 권장
- Windows 환경 권장
- `requirements.txt`에 정의된 패키지

## 설치

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 실행

```powershell
py -3 MacroGUI.py
```

또는 가상환경을 활성화한 뒤:

```powershell
python MacroGUI.py
```

## 사용 방법

1. `새 매크로`로 프로필을 만들거나 `_Script` 폴더의 기존 JSON 매크로를 선택합니다.
2. `추가` 버튼으로 액션을 직접 입력하거나 `기록기 열기`로 실제 입력을 기록합니다.
3. 필요한 경우 일련번호 입력 영역에 사용할 값을 한 줄씩 넣습니다.
4. `저장` 후 `즉시 실행` 또는 `예약 실행`을 사용합니다.

기본 즉시 실행 단축키는 `ctrl+1`이고, 기록기 중지 단축키는 `f8`입니다. 설정값은 `macro_gui/constants.py`에서 변경할 수 있습니다.

## 프로젝트 구조

```text
MacroGUI.py              # 애플리케이션 진입점
requirements.txt         # 런타임 의존성
macro_gui/
  app.py                 # QApplication 초기화
  main_window.py         # 메인 UI와 매크로 관리
  dialogs.py             # 액션 입력 다이얼로그
  recorder.py            # 입력 기록기
  workers.py             # 매크로 실행/예약 작업자
  utils.py               # 공통 유틸리티
  constants.py           # 액션/단축키/기본값
_Script/
  *.json                 # 매크로 프로필 저장 위치
```

## 주의 사항

- `keyboard`, `pynput`, `pyautogui`는 OS 권한이나 보안 정책의 영향을 받을 수 있습니다.
- 마우스 좌표 기반 매크로는 화면 해상도와 창 위치가 바뀌면 다르게 동작할 수 있습니다.
- 실행 중 마우스를 화면 모서리로 이동하면 PyAutoGUI fail-safe가 동작할 수 있습니다.
- 화면 캡처 결과는 `_Script/Capture/`에 저장되며 Git에는 포함하지 않습니다.
