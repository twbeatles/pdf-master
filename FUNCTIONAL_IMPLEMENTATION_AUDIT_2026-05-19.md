# PDF Master 기능 구현 리스크 감사

작성일: 2026-05-19

## 감사 범위

`README.md`, `CLAUDE.md`, 기존 `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-05-13.md`를 기준 문서로 삼고, 현재 코드의 Worker 실행 계약, UI 실행 경로, 저장/취소 처리, i18n, 패키징/검증 표면을 대조했다.

주요 확인 파일:

- `README.md`
- `CLAUDE.md`
- `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-05-13.md`
- `pyproject.toml`
- `pdf_master.spec`
- `.gitignore`
- `main.py`
- `src/core/worker_runtime/*`
- `src/core/worker_ops/*`
- `src/ui/main_window_worker.py`
- `src/ui/window_preview/*`
- `tests/*`

## 검증 결과

후속 구현 후 현재 checkout에서 실행한 검증:

| 검증 | 결과 |
| --- | --- |
| `python -m pytest -q` | 통과: 169 collected, 168 passed, 1 skipped |
| `python -m pyright` | 통과: 0 errors, 0 warnings |
| `$env:QT_QPA_PLATFORM='offscreen'; python main.py --smoke` | 통과: 앱 초기화 후 정상 종료 |
| `python -m pytest -q tests\test_worker_preflight.py tests\test_worker_auto_output_names.py tests\test_i18n_worker_hardcoded_smoke.py tests\test_worker_batch_watermark.py` | 통과 |
| `python -m pytest -q -rs tests\test_ai_service_gemini_smoke.py` | 이번 범위 제외: `PDF_MASTER_GEMINI_FILE_API_SMOKE=1`과 `GEMINI_API_KEY`가 필요한 opt-in smoke |

전체적으로 2026-05-13 감사 후속으로 정리된 split-package 구조, compatibility facade, Worker mode registry, PyInstaller hidden import, 기본 smoke 경로는 현재도 유지된다.

## 결론

F-01~F-04는 후속 구현으로 완료했다. 문서가 약속한 fail-fast, atomic save, i18n smoke 범위와 실제 구현 사이의 주요 drift는 해소되었고, Gemini File API live smoke(F-05)는 사용자 선택에 따라 이번 범위에서 제외했다.

## 발견 항목

### F-01. 접근 불가 파일 preflight 실패가 UI cleanup 신호 없이 끝날 수 있음

심각도: 높음

후속 상태: 완료. `inaccessible` PDF/비-PDF 입력이 기존 `err_file_access_denied` 메시지를 emit하도록 보강했고, 관련 OSError 회귀 테스트를 추가했다.

관련 근거:

- `src/core/pdf_validation.py:22`, `src/core/pdf_validation.py:34`는 `OSError`를 `PdfValidationResult(False, "inaccessible")`로 반환한다.
- `src/core/worker_runtime/preflight.py:57-88`의 `validate_file_size()`는 `missing`, `too_large`, `too_small`, `invalid_header`만 사용자 오류로 emit하고, 그 외 reason은 로그만 남긴 뒤 `False`를 반환한다.
- `src/core/worker_runtime/preflight.py:91-111`의 `validate_non_pdf_size()`도 `OSError`에서 로그만 남기고 error signal 없이 `False`를 반환한다.
- `src/ui/main_window_worker.py:113-122`는 custom `finished_signal`, `error_signal`, `cancelled_signal`에 UI cleanup을 연결한 뒤 busy 상태로 전환한다.

영향:

권한 문제, 잠긴 파일, 네트워크/OneDrive 일시 접근 실패처럼 `os.path.exists()`는 통과하지만 `getsize/open`이 실패하는 경우, Worker가 preflight에서 조용히 반환할 수 있다. 이때 `on_fail()`이 호출되지 않으면 진행 오버레이와 비활성화된 탭이 남는 사용자 체감 장애가 된다.

권장 조치:

- `inaccessible` reason을 `err_file_access_denied` 또는 신규 `err_file_inaccessible` i18n key로 emit한다.
- PDF와 비-PDF 입력 각각에 대해 `os.path.getsize` 또는 `open` OSError monkeypatch 회귀 테스트를 추가한다.
- preflight가 `False`를 반환하는 모든 경로가 반드시 error/cancel signal을 emit한다는 구조 테스트를 추가한다.

### F-02. `extract_text`가 문서의 atomic text save 계약을 우회함

심각도: 중간

후속 상태: 완료. `extract_text()`가 직접 파일 쓰기 대신 `_atomic_text_save()`를 사용하도록 변경했고, atomic save 경유 및 자동 출력명 회귀 테스트를 추가했다.

관련 근거:

- `README.md:631`과 `CLAUDE.md:706`은 TXT/MD/report 또는 Worker text output이 atomic temp-write + replace로 정리됐다고 설명한다.
- 대부분의 text/report mode는 `_atomic_text_save()`를 사용한다.
- 하지만 `src/core/worker_ops/extract_ops.py:107-108`의 `extract_text()`는 `with open(out_path, "w", encoding="utf-8")`로 직접 쓴다.
- 같은 함수는 `output_dir` 신규 파일일 때만 `created_output_paths`를 기록하고, 단일 `output_path` overwrite에 대해서는 atomic replace/cancel checkpoint가 없다.

영향:

텍스트 추출 중 쓰기 실패, 앱 종료, 취소 타이밍이 겹치면 기존 TXT가 부분적으로 덮이거나 cleanup 추적에서 빠질 수 있다. 현재 문서/설계가 강조하는 atomic output 정책과도 어긋난다.

권장 조치:

- `extract_text()`의 직접 `open()`을 `_atomic_text_save()`로 교체한다.
- 단일 `output_path`와 다중 `output_dir` 모두에서 기존 파일 보존/신규 파일 rollback 동작을 테스트한다.
- `rg "with open(out_path"` 같은 회귀 검사를 test에 넣어 text-output helper 우회를 막는다.

### F-03. Worker i18n smoke가 변수로 조립된 hardcoded 메시지를 놓침

심각도: 중간

후속 상태: 완료. 병합 완료/건너뜀 메시지와 batch 실패 row를 KO/EN i18n key로 이동했고, `emit(variable)`의 같은 함수 내 hardcoded string 조립도 감지하도록 worker i18n smoke를 강화했다.

관련 근거:

- `README.md:28`, `README.md:430`, `CLAUDE.md:27`은 Worker 결과/상태 메시지를 KO/EN i18n catalog로 관리한다고 설명한다.
- `tests/test_i18n_worker_hardcoded_smoke.py:27-31`은 `emit("literal")` 또는 `emit(f"...")`만 잡는다.
- `src/core/worker_ops/compose_ops.py:78-81`은 `result_msg = f"✅ 병합 완료!..."; result_msg += f"...건너뜀"; finished_signal.emit(result_msg)`로 변수에 담긴 한국어 f-string을 emit한다.
- 간단한 AST 추적으로 확인한 결과, `compose_ops.py`와 `batch_ops.py` 모두 변수 조립 후 emit 경로가 있다. `batch_ops.py`의 파일별 실패 상세는 동적 정보라 허용 가능하지만, `compose_ops.py`의 병합 완료 메시지는 명확히 catalog 후보이다.

영향:

영어 UI/locale에서도 병합 완료 메시지는 한국어로 표시될 수 있다. 테스트가 통과하기 때문에 이후에도 같은 패턴이 재발할 수 있다.

권장 조치:

- 병합 완료/건너뜀 메시지를 `msg_merge_done`, `msg_merge_skipped` 같은 KO/EN catalog key로 이동한다.
- i18n smoke를 보강해 `emit(variable)`일 때 같은 함수 안에서 string literal 또는 f-string으로 할당/증분된 변수를 추적한다.
- 예외 상세처럼 파일명/라이브러리 메시지를 포함해야 하는 동적 append는 allowlist 또는 helper 사용으로 구분한다.

### F-04. PDF -> 이미지 변환은 binary output atomic 정책 밖에 남아 있음

심각도: 낮음

후속 상태: 완료. `_atomic_pixmap_save()` helper를 추가해 PDF -> 이미지 변환도 temp-save + `os.replace()` 경로로 저장하고, 신규 이미지 출력 추적 및 취소 cleanup 회귀 테스트를 갱신했다.

관련 근거:

- `src/core/worker_ops/transform_ops.py:45-78`의 `convert_to_img()`는 `pix.save(save_path)`로 직접 이미지를 저장한 뒤 신규 파일만 `created_output_paths`에 기록한다.
- 이미지/첨부 추출 경로는 `_atomic_binary_save()`를 쓰는 쪽으로 정리되어 있다.

영향:

`pix.save()` 중 실패 또는 프로세스 종료가 발생하면 부분 이미지가 남을 수 있다. GUI에서 사용자가 기존 출력 폴더를 지정하는 기능 특성상, 대량 변환 시 잔여 파일 정리가 사용자의 신뢰에 영향을 줄 수 있다.

권장 조치:

- PyMuPDF pixmap이 지원하는 포맷은 `pix.tobytes(fmt)` + `_atomic_binary_save()`로 저장하는 방식을 검토한다.
- 포맷별 `tobytes` 지원 차이가 있으면 임시 파일 저장 후 `os.replace()`를 적용하는 별도 helper를 만든다.
- 취소 시 생성된 이미지 파일만 제거되는 회귀 테스트를 유지/확장한다.

### F-05. Gemini File API 실연동은 기본 검증에서 빠져 있음

심각도: 낮음

후속 상태: 이번 범위 제외. Gemini live smoke는 비용/키가 필요한 opt-in 검증으로 유지한다.

관련 근거:

- 전체 pytest 결과에서 1개 skip이 있었고, `tests/test_ai_service_gemini_smoke.py`는 `PDF_MASTER_GEMINI_FILE_API_SMOKE=1` 없이는 실행되지 않는다.
- 문서도 Gemini File API live validation이 opt-in임을 명시한다.

영향:

비용/키가 필요한 테스트라 기본 skip은 타당하다. 다만 SDK 응답 schema, 업로드 파일 lifecycle, rate-limit/retry 정책은 기본 CI/로컬 검증으로는 보장되지 않는다.

권장 조치:

- 릴리스 전 keyed 환경에서 opt-in Gemini smoke를 별도 체크리스트로 실행한다.
- 가능하면 SDK fake client 기반의 schema/streaming/session cleanup 단위 테스트를 더 늘려 live smoke 의존도를 낮춘다.

## 현재 양호한 부분

- `OPERATION_SPECS`와 UI `run_worker()` 정적 계약 테스트가 있어 mode별 필수 인자 drift를 잘 막고 있다.
- Worker handler split 이후에도 public facade/import 경로 보존 테스트가 유지된다.
- `main.py --smoke`가 실제 QApplication 초기화와 종료 cleanup을 검증한다.
- `pdf_master.spec`는 split-package 하위 모듈을 `collect_submodules()`로 수집하고 있어 현재 구조와 대체로 맞다.
- `.gitignore`는 build/dist/cache/egg-info/atomic temp 산출물을 포괄한다.

## 우선순위 제안

1. F-01~F-04는 후속 구현 완료.
2. F-05는 릴리스 전 keyed 환경에서 별도 opt-in으로 실행한다.

## 참고

이번 문서는 감사 결과와 같은 날 진행한 후속 구현 결과를 함께 기록한다.
