# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

상위 폴더의 `d:\000-클로드-프로젝터\CLAUDE.md`(인사, 쉬운 설명, 계획 먼저, 기록, 질문하기, 작업 원칙 7~9)도 함께 적용된다. 여기에는 이 게임 폴더에만 해당하는 것과 상위 규칙과 다른 점만 적는다.

## 상위 규칙과 다른 점 (코딩 작업)
- 코드(`index.html`, 이 파일)는 이 폴더에서 바로 고친다. 코드 파일에는 날짜를 붙이지 않는다.
- 스크린샷, 기획안 같은 산출물은 상위 폴더 `d:\000-클로드-프로젝터\output\`에 `YYYYMMDD_내용.확장자`로 저장한다.
- 작업 기록은 상위 폴더의 `d:\000-클로드-프로젝터\history.md` 맨 아래에 이어 쓴다.
- PowerShell에서는 `npm`, `npx` 대신 `npm.cmd`, `npx.cmd`를 쓴다(지금은 필요 없음).

## 프로젝트
- 블록 피하기 게임. 같은 게임이 두 판으로 있다. 규칙이나 숫자를 바꾸면 두 파일을 함께 고칠지 사용자에게 묻는다.
  - `index.html`: HTML, CSS, JS(canvas)가 파일 하나에 다 들어 있다. 설치나 빌드는 없다.
  - `game.py`: 파이썬 3.14와 pygame-ce 2.5.8로 만들었다. 함수 이름은 index.html을 snake_case로 바꾼 것(`level_params`, `make_row` 등)이다. 상태는 `S`(SimpleNamespace)에 모았다. BEST는 같은 폴더의 `best.txt`에 저장한다. 소리는 파일 없이 `tone()`으로 만든다.
- 기획안: `d:\000-클로드-프로젝터\output\20261126_블록피하기_기획안.md`. 숫자나 규칙을 바꾸면 기획안과 다르다는 점을 알려 준다.

## 실행과 확인
- 실행: `index.html`을 더블클릭해 크롬에서 연다.
- 자체 검사: 페이지가 열릴 때 `console.assert`로 `hit`, `levelParams`, `makeRow`를 검사한다. 개발자 도구 콘솔에 `Assertion failed`가 없으면 통과다.
- 브라우저 자동 확인: agent-browser 프로그램은 이 PC에 없다. 대신 Node(내장 WebSocket)로 크롬을 headless로 띄우고 DevTools 프로토콜로 키 입력, `Runtime.evaluate`, 스크린샷을 한다. 최상위 `let` 변수(`state`, `score`, `lane`, `blocks` 등)는 evaluate에서 바로 읽고 쓸 수 있다.
- 소리는 자동으로 확인할 수 없다. 사용자가 직접 들어 봐야 한다.
- game.py 실행: `python game.py`. 불러올 때 `assert`로 자체 검사를 한다.
- game.py 화면 없이 확인: 환경 변수 `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`를 설정한다. 그다음 `import game`을 하고 `handle_key()`, `update(1/60)`, `draw()`를 직접 부르고 `pygame.image.save(game.screen, ...)`로 화면을 저장한다. 실제 BEST가 바뀌지 않게 `game.BEST_FILE`은 임시 경로로 바꿔 둔다.

## 코드 구조 (여러 곳을 읽어야 보이는 것)
- 화면 크기(index.html만): `W`, `H`, `CX`, `PY`는 고정값이 아니다. `resize()`가 500x420을 짧은 쪽 기준으로 키우고, 남는 쪽은 장면을 늘려서 화면을 가득 채운다(세로 폰은 W=500에 H가 길어지고, 넓은 PC는 H=420에 W가 넓어진다). 화면 요소 위치는 숫자로 고정하지 말고 `W`, `H`, `CX` 기준으로 정한다. game.py는 500x420 고정 창에 밤 도시 배경이고, index.html은 가로수 길(`drawTree`, 점선과 같은 `dash` 위치로 흐름)이다.
- 원근: 깊이 `z`는 0(위, 먼 곳)부터 1(아래, 가까운 곳)까지다. 화면 y는 `zToY = H·z²`, 도로 반폭은 `halfW(y)`로 y에 비례한다. 차선 x는 `laneX(lane, y)`이다. 블록 크기도 `laneW(y)`를 따른다.
- 플레이어: `lane`은 목표 차선(정수), `px`는 실제 위치(소수)다. `px`가 `lane`을 지수적으로 따라가며(약 0.15초) 미끄러진다. 충돌 판정은 `px` 기준이라 두 차선 사이에 걸치면 양쪽 블록에 모두 맞는다.
- 흐름: `requestAnimationFrame` → `update(dt)` → `draw()`. `dt`는 최대 0.05초로 자른다.
- 입력(index.html만): 키보드와 터치·마우스(`pointerdown`)가 같은 `tryStart()`, `move(d)`를 부른다. 게임 중에는 화면 왼쪽 반/오른쪽 반으로 방향을 정하고, 그 밖의 상태에서는 화면 어디를 눌러도 시작한다. 시작 버튼은 그림만 있다. game.py에는 터치가 없다.
- 상태: `ready` → (Space) → `playing` → (충돌 `crash`) → `over` → (0.4초 뒤 Space) → `reset()`. 흔들림, 파편, 깜빡임은 `over`에서도 `update` 맨 앞에서 계속 갱신된다.
- 난이도: 속도, 줄 간격, 2개 줄 확률은 `levelParams(level)` 한 곳에서만 정한다. 레벨은 100점(10초)마다 오른다. 난이도 조정은 이 함수만 고친다. `makeRow`는 3개 줄(길 막힘)을 만들지 않는다.
- 소리: Web Audio의 `sfx(type)`(`move`, `hit`, `up`)이다. `AudioContext`는 첫 Space 때 만든다(크롬의 자동 재생 제한 때문).
- BEST: `localStorage`의 `dodgeBest` 키에 저장한다.
