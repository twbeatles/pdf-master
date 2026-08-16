# Project Audit

## 1. Executive Summary

PDF Master는 PyQt6 UI, `WorkerThread` 기반 PDF 작업 계층, PyMuPDF 작업 모듈, 설정/AI 캐시 계층으로 구성된 Windows 우선 PDF 유틸리티다. 새 GitHub Release 업데이트는 Ed25519 서명과 SHA-256·크기 검증을 적용해 신뢰 경계를 잘 설정했다.

전체 위험도는 **High**다. 기존 Worker 경로는 OperationSpec, 취소 정리, 다수 회귀 테스트로 비교적 보호되지만, 업데이트 경로는 실제 릴리스·교체·롤백 E2E 검증이 없다. 특히 릴리스 매니페스트 게시 실패 가능성, 중복 업데이트 경쟁 조건, 설치 실패 결과 미전달, 버전 중복 관리가 첫 실제 릴리스 전 해결 대상이다.

감사 시 `python -m pytest -q`는 **327 passed, 1 skipped**였다. 이는 기존 회귀 신호로는 긍정적이나 update installer와 GitHub Actions 릴리스 흐름을 검증하지 않는다.

## 2. Project Understanding

README/CLAUDE에 따르면 프로젝트는 PDF 병합·변환·편집·보안·추출·AI 기능을 제공한다. Python 3.10+, PyInstaller 단일 EXE를 전제로 하며, `pyright`, `pytest`, `main.py --smoke`가 기본 검증 기준이다. UI는 메인 스레드만 갱신하고 장기 작업은 취소 가능한 Worker로 처리한다.

CodeGraph가 확인한 핵심 흐름은 다음과 같다.

```text
main.py -> PDFMasterApp
  -> MainWindowWorkerMixin.run_worker() [69 callers]
     -> WorkerThread [122 callers]
        -> WorkerRuntimeMixin.run() -> OperationSpec dispatch -> worker_ops

PDFMasterApp -> UpdateMixin
  -> check_for_updates() thread -> download/verify manifest
  -> _offer_update() -> stage_update() -> helper EXE
  -> main.py --apply-update -> apply_update()
```

설정은 사용자 홈 JSON을 임시 파일+`os.replace`로 저장하고, AI 캐시는 정규화 경로와 mtime을 키로 사용한다. 업데이트는 공개키를 번들에 포함하고, 서명 검증 후에만 다운로드·해시/크기 검증·별도 프로세스 EXE 교체를 수행한다.

## 3. High-Risk Issues

* 위치: `.github/workflows/release.yml` — Checkout, `Publish update manifest`
* 문제: 기본 shallow checkout인데 `git merge-base --is-ancestor $GITHUB_SHA origin/main`으로 태그 커밋의 main 포함 여부를 검사한다. 과거 main 커밋 태그/재발행 때 공통 조상이 shallow history에 없으면 실제 포함 관계와 달리 실패할 수 있다.
* 영향: Release 자산은 생겼지만 `updates/latest.json` 게시가 실패하여 설치 앱이 새 릴리스를 발견하지 못할 수 있다.
* 근거: Checkout에 `fetch-depth: 0`이 없고, 게시 단계가 전체 이력 판단을 수행한다.
* 권장 수정 방향: `fetch-depth: 0` 또는 명시적 full fetch를 사용하고 publication 재시도를 분리한다.
* 우선순위: High

* 위치: `src/ui/update_mixin.py:35-64`, `src/core/update_installer.py:40-72`
* 문제: 업데이트 확인/다운로드/설치의 단일 실행 guard가 없다. 시작 예약 확인과 메뉴 연속 클릭이 각각 스레드를 만들고, 같은 manifest가 둘 이상 도착하면 여러 helper가 같은 EXE와 `.exe.bak`를 경쟁적으로 처리한다.
* 영향: 교체 실패, 백업 손실, 중복 안내·재실행 누락이 발생할 수 있다.
* 근거: 매 호출이 `threading.Thread(...).start()`하며 `_offer_update()`에 in-progress 상태가 없다. installer backup 이름은 target마다 고정이다.
* 권장 수정 방향: UI 소유 `idle/checking/downloading/applying` 상태 머신, 메뉴 비활성화, helper target 잠금/고유 result 파일을 적용한다.
* 우선순위: High

* 위치: `src/core/update_installer.py:46-72`, `src/ui/update_mixin.py:57-64`
* 문제: helper 교체 결과가 원래 앱이나 다음 실행에 전달되지 않는다. helper는 숨김 프로세스이고 `apply_update()`는 오류를 기록·표시하지 않고 exit code만 반환한다.
* 영향: 파일 잠금, 권한, smoke 실패 및 롤백 실패 때 사용자는 앱이 사라진 것으로 보며 원인을 알 수 없다. 기존 EXE 재시작도 보장되지 않는다.
* 근거: helper 인자에 result 파일/IPC가 없고 예외 처리도 `return 4`만 한다.
* 권장 수정 방향: 원자적 result JSON(상태/오류/롤백)을 기록하고 다음 기동에서 한 번 소비해 표시한다. 실패/롤백 때 기존 EXE를 재시작하고 로그를 남긴다.
* 우선순위: High

* 위치: `src/core/_constants_impl/values.py:5`, `pyproject.toml`, `pdf_master.spec`, `.github/workflows/release.yml:41,57`
* 문제: 버전이 세 곳에 중복돼 있다. workflow는 `VERSION`만 태그와 비교하지만 spec EXE 이름과 pyproject 버전은 별도 고정값이다.
* 영향: 상수만 올리면 workflow가 새 이름의 EXE를 찾지 못해 릴리스가 실패하거나 서로 다른 버전의 산출물이 생길 수 있다.
* 근거: 현재 모두 `4.5.6`이지만 manifest 단계는 `dist/PDF_Master_v$version.exe`를 요구하고 spec/pyproject 동기화 검사는 없다.
* 권장 수정 방향: 버전 단일 소스 또는 workflow의 3-way 검증과 artifact-name 테스트를 추가한다.
* 우선순위: High

* 위치: `src/core/update_installer.py:17-37,40-72`
* 문제: updater는 `.exe`/`LOCALAPPDATA`를 전제하지만 UI는 frozen 환경이면 플랫폼과 무관하게 설치를 제안한다.
* 영향: 향후 비-Windows 번들을 배포하면 다운로드 후 종료했지만 설치가 실패할 수 있다. 현재 README 배포 대상이 Windows라 현 영향은 제한적이다.
* 근거: stage/apply가 EXE만 허용하고 `_offer_update()`에 플랫폼 guard가 없다.
* 권장 수정 방향: Windows 전용 동작을 코드·문서에 명시하고 다른 플랫폼은 비활성화한다.
* 우선순위: Medium

## 4. Potential Functional Gaps

* **추정:** 다운로드가 `_offer_update()` UI 스레드에서 직접 `urlopen`/파일 쓰기를 수행한다. 큰 EXE에서는 진행률·취소 없이 창이 멈출 수 있다.
* **추정:** 성공 뒤 `pdf-master-update-helper-*.exe` 삭제가 없어 반복 업데이트 시 `%LOCALAPPDATA%/PDFMaster/updates`에 helper가 누적된다.
* **추정:** `workflow_dispatch`는 version 입력값 없이 `github.ref_name`을 사용하므로 브랜치에서 수동 실행하면 버전 정규식 검사를 통과하지 못한다.
* **확실:** README/CLAUDE는 자동 업데이트, Windows 제약, 실패 복구, 버전 변경 체크리스트, `PM_UPDATE_*` secret 책임 범위를 설명하지 않는다. 코드/워크플로와 문서가 불일치한다.
* **확실:** update 전용 테스트는 `tests/test_update_manifest.py` 하나뿐이며 서명 수락·변조 거부·동일 버전만 다룬다. 다운로드, installer, rollback, 중복 실행, workflow publication 테스트가 없다.
* **추정:** manifest 만료는 365일 고정이다. 1년간 릴리스가 없으면 정상 앱이 업데이트 실패로 취급된다. 정책과 재발행 절차를 명시할 필요가 있다.

## 5. Recommended Fix Plan

### 1단계는 즉시 수정해야 할 문제

1. Release workflow를 full-history checkout으로 바꾸고 main 포함성 검사를 검증한다.
2. updater에 단일 실행 상태 머신과 helper 잠금을 추가한다.
3. helper result 파일, 롤백 결과 표시, 실패 시 기존 EXE 재실행을 구현한다.
4. 버전 단일 소스화 또는 constants/pyproject/spec의 CI 동기화 검사를 추가한다.

### 2단계는 안정성 개선

1. 다운로드를 QThread/Worker로 이동해 진행률·취소·네트워크 오류를 제공한다.
2. Windows platform guard와 staging/helper 정리 정책을 추가한다.
3. redirect 최종 URL·허용 호스트·timeout 정책을 문서화하고 로그를 보강한다.
4. README/CLAUDE에 릴리스 절차와 update 운영 문서를 추가한다.

### 3단계는 구조 개선

1. UpdateService(상태/네트워크), Installer(교체), UI Controller를 분리한다.
2. manifest publication을 재시도 가능한 독립 workflow/job으로 분리한다.
3. 버전·asset 이름·manifest 메타데이터를 하나의 build metadata에서 생성한다.

## 6. Test Recommendations

1. installer 임시 EXE 성공 교체, hash/size 실패, smoke 실패 rollback, backup 복구 실패를 테스트한다.
2. 자동+수동 확인 동시 호출에서도 하나의 다운로드/helper만 실행되는 UI 상태 테스트를 추가한다.
3. mock HTTPS 응답으로 초과 크기, 잘린 응답, HTTPS→HTTP redirect, 해시 불일치를 검증한다.
4. helper result JSON의 성공/롤백/실패 기록과 다음 기동의 한 번만 소비·표시를 검증한다.
5. constants/pyproject/spec/asset 이름의 버전 동기화와 manifest URL 생성을 테스트한다.
6. shallow/full checkout에서 main 포함성 검사를 재현하고 workflow_dispatch의 ref 처리도 검증한다.
7. Windows VM 또는 Actions E2E로 이전 EXE에서 stage→교체→smoke→재기동 및 고의 실패 rollback을 검증한다.
