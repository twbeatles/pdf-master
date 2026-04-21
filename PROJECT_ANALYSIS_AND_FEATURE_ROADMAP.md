# PDF Master 프로젝트 분석 및 기능 확장 로드맵
작성일: 2026-04-19
기준 버전: v4.5.5
참조 문서: `README.md`, `README_EN.md`, `CLAUDE.md`, `GEMINI.md`, `pdf_master.spec`, `pyproject.toml`

## 1. 요약

PDF Master는 이미 기능 폭이 넓고, UI/worker/runtime/test/build 계층이 비교적 잘 분리된 데스크톱 PDF 도구입니다. 이번 정리 이후 기준선은 다음과 같습니다.

- 미리보기는 `QPdfDocument + QPdfView + QPdfSearchModel + QPdfBookmarkModel + QPdfPageNavigator` 기반으로 동작합니다.
- AI 계층은 `google-genai` 단일 SDK 기준으로 정리되어 있습니다.
- worker dispatch는 `OperationSpec` 메타데이터를 중심으로 확장되고 있습니다.
- 저장 전략은 `fast`, `compact`, `web` save profile 중심으로 통합되었습니다.
- `pyproject.toml`이 canonical manifest이며 `requirements-dev.txt`는 호환 shim입니다.

즉, 이 프로젝트의 다음 단계는 "새 기능을 무작정 덧붙이는 것"보다 "이미 있는 엔진을 더 잘 활용하고 구조적 일관성을 유지하면서 확장하는 것"에 가깝습니다.

## 2. 현재 구조 평가

### 강점

- `src/core/worker_runtime/*`와 `src/core/worker_ops/*` 분리로 UI와 실제 처리 로직의 경계가 비교적 명확합니다.
- Undo/Redo, preview restore, same-path overwrite 대응처럼 실사용에서 중요한 안전장치가 이미 갖춰져 있습니다.
- `tests/`가 기능 회귀 중심으로 꽤 넓게 깔려 있습니다.
- README/가이드 문서와 빌드 설정, 검증 명령이 서로 맞물리도록 관리되고 있습니다.

### 주의할 지점

- `src/core/worker_ops/_pdf_impl.py`는 여전히 큰 편이라 장기적으로는 추가 분해가 필요합니다.
- `src/ui/tabs_advanced/builders.py`도 UI 생성 코드가 많이 모여 있어 유지보수 비용이 큽니다.
- AI 실통신 검증은 로컬 환경에 `google-genai`가 설치되어 있어야 끝까지 점검할 수 있습니다.

## 3. 이번 구현 이후 기준 상태

### 미리보기 / 탐색

- 외부 프로그램이 preview 대상 PDF를 atomic replace해도 watcher + retry로 자동 재로드됩니다.
- same-path 저장 시 preview 문서를 먼저 닫고, 작업 후 view state를 포함해 복원합니다.
- page setup과 print preview는 분리된 printer lifecycle을 사용합니다.
- rotate/AI/thumbnail 흐름은 preview 기준 문서와 페이지를 더 일관되게 공유합니다.

### AI

- `google-generativeai` 레거시 경로는 제거되었습니다.
- File API fallback은 업로드 제약 오류에서만 허용됩니다.
- 채팅 세션 키는 `(model, abs_path, mtime_ns)` 기준입니다.
- 채팅 삭제는 현재 PDF의 저장 히스토리와 SDK 세션만 초기화합니다.

### 추출 / 저장

- Markdown 추출은 `auto`, `native`, `text` 모드를 지원합니다.
- front matter, page marker, image/table placeholder 옵션이 추가되었습니다.
- 압축은 quality 문자열보다 `save_profile`을 우선 사용합니다.
- batch compress도 중앙 save profile 규칙을 따릅니다.

### 런타임 / 레지스트리

- `OperationSpec`는 `required_kwargs`, `result_payload_keys`, `refresh_preview`, `cancel_cleanup`, `output_extensions`를 포함합니다.
- preflight는 required kwargs 검증을 수행합니다.
- UI payload 후처리도 spec metadata를 기준으로 맞춰졌습니다.

## 4. 의존성 활용 관점에서 유망한 확장 포인트

### PyMuPDF

가장 많은 확장 여지가 있습니다.

- OCR 연동
- richer markdown export
- HTML/CSS 기반 문서 생성
- 저장 프로필 세분화
- 첨부 파일 관리 강화
- 문서 비교 결과 고도화

특히 OCR과 richer markdown export는 실사용 가치가 높습니다.

### PyQt6 / QtPdf

현재 구조와 가장 잘 맞는 방향입니다.

- 검색 결과 사이드 패널 UX 보강
- 북마크/목차 탐색 강화
- preview 상태 표시 개선
- watcher 기반 외부 변경 알림 UX 개선
- 인쇄 설정 preset 확장

### google-genai

AI는 아직 "가능성 대비 활용도"가 더 올라갈 수 있습니다.

- 실제 File API 기반 document understanding 검증
- structured output 스키마 확장
- streaming 결과 표현 개선
- session-aware chat UX 고도화
- 요약/채팅/키워드 외 문서 분석 카드 확장

## 5. 추가 개선 우선순위

### 1순위

- `google-genai` 설치 환경에서 실제 업로드/스트리밍 smoke test 수행
- `_pdf_impl.py` 추가 분해
- 고급 탭 builder 분리
- search/bookmark UX 세부 polish

### 2순위

- OCR 기능 설계 및 optional dependency 전략 결정
- compare/report 결과 UI 구조화
- AI 결과 카드형 UI 정리

### 3순위

- 템플릿 기반 문서 생성
- 첨부 파일 제거/교체 기능
- journalling 또는 더 고도화된 undo 전략 검토

## 6. `.spec`, `.gitignore`, 문서 정합성 점검 결과

### `pdf_master.spec`

현재 기준으로 적절합니다.

- `PyQt6.QtPdf`, `PyQt6.QtPdfWidgets`가 포함됩니다.
- `google-genai` only 기준으로 정리되어 있습니다.
- preview runtime에서 중요한 `src.ui.zoomable_preview` 경로가 유지됩니다.
- 이번 정리에서 `src.core.path_utils`, `src.core.worker_runtime.save_profiles`도 명시적으로 보강했습니다.

### `.gitignore`

현재 빌드/검증 워크플로와 잘 맞습니다.

- `build/`, `dist/`, `.pytest_tmp/`, `.pytest_cache/`, `.pyright/`, `*.egg-info/` 제외
- 이번 점검에서 `.eggs/`, `pip-wheel-metadata/`, `*.whl`, `*.tar.gz`도 추가해 패키징 산출물 누수를 더 줄였습니다.

### 문서

README / EN / CLAUDE / GEMINI 문서는 다음 기준으로 동기화되었습니다.

- `pyproject.toml` 중심 설치
- `requirements-dev.txt` shim 설명
- `google-genai` only
- QtPdf preview runtime
- external preview auto-reload
- current-PDF chat clear semantics
- markdown option / save profile UX
- `python -m pyright`
- `python -m pytest -q`
- `python -m build`
- `python -m PyInstaller pdf_master.spec --clean`

## 7. 검증 기준

이번 정리 기준 로컬 검증 명령은 아래입니다.

```bash
python -m pytest -q
python -m pyright
python -m build
python -m PyInstaller pdf_master.spec --clean
```

## 8. 결론

PDF Master는 현재 "기능이 부족한 프로젝트"가 아니라 "좋은 기반 위에 선택적으로 고도화할 수 있는 프로젝트"입니다. 특히 PyMuPDF, QtPdf, `google-genai` 세 축을 제대로 살리면 문서 추출, 탐색, AI 분석 경험을 더 크게 끌어올릴 수 있습니다.

가장 실효성 높은 다음 단계는 아래 순서입니다.

1. `google-genai` 실통신 검증
2. `_pdf_impl.py` / advanced builder 구조 정리
3. OCR 및 richer extraction 설계
4. 탐색/분석 UX polish

---

## 2026-04-21 Implementation Status Addendum

The following roadmap-adjacent stabilization items are now implemented in the repository:

- Batch output collision avoidance now uses deterministic `*_processed`, `*_processed__2`, ... naming and treats case-only collisions as the same target family.
- AI flows now expose fallback/truncation metadata end-to-end, including worker payloads and user-visible labels in the AI tab.
- Gemini uploaded-file lifecycle cleanup now covers cache eviction, current-PDF chat clearing, and application shutdown.
- Visual diff PDF generation now uses bidirectional block overlays with duplicate-aware `Counter` comparison and page legends.
- Undo snapshot failures are now surfaced to the user as explicit "undo unavailable" warnings.
- API key persistence now requires explicit confirmation before any plaintext settings-file fallback.
- Worker text outputs now use atomic save/replace semantics for TXT, Markdown, comparison reports, and saved AI summaries.
- `pdf_master.spec` and the core docs were re-synced to the current validation/build contract before package builds.
