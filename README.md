# PDF Master v4.5

📑 **올인원 PDF 편집 프로그램** - PyQt6 기반 데스크톱 앱

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-fitz-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

[🇺🇸 English README](README_EN.md) | [🇰🇷 한국어](#)

---

## 📋 목차

- [주요 기능](#-주요-기능)
- [설치 및 실행](#-설치-및-실행)
- [사용 방법](#-사용-방법)
- [단축키](#️-단축키)
- [빌드](#-빌드-pyinstaller)
- [프로젝트 구조](#-프로젝트-구조)
- [변경 이력](#-변경-이력)

---

## ✨ 주요 기능

### 📄 PDF 병합 및 변환
| 기능 | 설명 | 지원 형식 |
|------|------|----------|
| **PDF 병합** | 여러 PDF를 하나로 합치기 | 드래그 앤 드롭 지원 |
| **PDF → 이미지** | 페이지별 이미지 변환 | PNG, JPG, WEBP, BMP, TIFF |
| **이미지 → PDF** | 여러 이미지를 PDF로 합치기 | PNG, JPG, BMP, GIF, WEBP |
| **텍스트 추출** | PDF에서 텍스트 추출 | TXT 저장 |

### ✂️ 페이지 편집
| 기능 | 설명 |
|------|------|
| **페이지 추출** | 원하는 페이지만 분리 (예: 1-3, 5, 7-10) |
| **페이지 삭제** | 선택한 페이지 제거 |
| **페이지 회전** | 90°, 180°, 270° 회전 |
| **페이지 순서 변경** | 드래그 앤 드롭으로 순서 재배치 |
| **페이지 번호 삽입** | 위치/형식/폰트 커스텀 (Page 1 of N, 1/N 등) |
| **빈 페이지 삽입** | 원하는 위치에 빈 페이지 추가 |
| **페이지 복제** | 선택한 페이지 복사 |
| **페이지 역순 정렬** | 전체 페이지 순서 뒤집기 |
| **페이지 크기 변경** | A4, A3, Letter, Legal 등 |

### 🔒 보안 및 보호
| 기능 | 설명 |
|------|------|
| **PDF 암호화** | AES-256 암호 설정 |
| **PDF 복호화** | 암호 해제 |
| **워터마크** | 텍스트/타일 워터마크 (투명도, 회전, 위치 조절) |
| **이미지 워터마크** | 위치(9개), 크기, 투명도 조절 (v4.5 개선) |
| **스탬프 추가** | 기밀, 승인됨, 사본, DRAFT 등 |

### 🔧 고급 편집
| 기능 | 설명 |
|------|------|
| **PDF 분할** | 각 페이지별 또는 범위별 분리 |
| **PDF 압축** | 고/중/저 압축률 선택 |
| **PDF 크롭** | 여백 자르기 |
| **메타데이터 편집** | 제목, 저자, 주제, 키워드 수정 |
| **PDF 비교** | 두 PDF 차이점 분석 |

### 📝 주석 및 마크업
| 기능 | 설명 |
|------|------|
| **텍스트 하이라이트** | 형광펜 효과 |
| **스티키 노트** | 메모 추가 |
| **밑줄/취소선** | 텍스트 마크업 |
| **도형 그리기** | 사각형, 원, 선 추가 (v4.5) |
| **하이퍼링크 추가** | URL/페이지 이동 링크 (v4.5) |
| **텍스트 상자 삽입** | PDF에 텍스트 직접 추가 (v4.5) |
| **텍스트 교정** | 민감 정보 영구 삭제 |
| **배경색 추가** | 페이지 배경 변경 |
| **프리핸드 서명** | 손글씨 서명 삽입 |

### 📊 데이터 추출
| 기능 | 설명 | 출력 |
|------|------|------|
| **링크 추출** | 문서 내 URL 목록 | 리스트 표시 |
| **이미지 추출** | 포함된 이미지 추출 | PNG/JPG 저장 |
| **테이블 추출** | 표 데이터 추출 | CSV 저장 |
| **북마크 추출** | 목차 구조 추출 | 리스트 표시 |
| **Markdown 변환** | PDF → Markdown | MD 저장 |
| **첨부파일 관리** | 첨부파일 추가/추출 | 다양한 형식 |

### 🤖 AI 기능 (Gemini API)
| 기능 | 설명 |
|------|------|
| **PDF 요약** | AI 기반 문서 요약 (한국어/영어) |
| **PDF 채팅** | PDF 내용에 대해 AI에게 질문하기 (v4.5) |
| **키워드 추출** | AI 기반 핵심 키워드 추출 (v4.5) |
| **요약 스타일** | 간결/상세/글머리 기호 선택 |
| **페이지 제한** | 요약할 최대 페이지 수 설정 |

> **참고**: AI 기능은 `google-genai` 패키지와 Gemini API 키가 필요합니다.

### 🎨 UI/UX
- **다크/라이트 테마** - 프리미엄 글래스모피즘 디자인
- **진행 오버레이** - 작업 중 취소 가능한 풀스크린 다이얼로그
- **토스트 알림** - 비침습적 알림 시스템
- **드래그 앤 드롭** - 파일 추가, 페이지 순서 변경
- **줌/패닝 미리보기** - 마우스 휠 줌, 드래그 이동
- **썸네일 그리드** - 모든 페이지 한눈에 보기
- **Undo/Redo** - 페이지 삭제, 회전, 압축 등 실행 취소
- **다국어 지원** - 한국어/영어 자동 감지 및 설정 가능 (v4.4)

---

## 🚀 설치 및 실행

### 요구 사항
- Python 3.10 이상
- Windows / macOS / Linux

### 의존성 설치
```bash
# 필수 패키지
pip install PyQt6 PyMuPDF

# AI 기능 사용 시 (선택)
pip install google-genai

# 또는 기존 SDK (deprecated)
pip install google-generativeai
```

### 실행
```bash
python main.py
```

---

## 📖 사용 방법

### 1. PDF 병합
1. **병합** 탭 선택
2. 파일을 드래그 앤 드롭하거나 **파일 추가** 버튼 클릭
3. 목록에서 순서 조정 (드래그로 이동 가능)
4. **병합 실행** 클릭 → 저장 위치 선택

### 🔄 언어 변경 (Change Language)
1. 메뉴 바에서 **Language** (🌐) 클릭
2. **Korean** 또는 **English** 선택
3. 앱 재시작 후 적용됨

### 2. PDF → 이미지 변환
1. **변환** 탭 선택
2. PDF 파일 선택
3. 출력 형식 선택 (PNG, JPG, WEBP 등)
4. DPI 설정 (기본: 200)
5. **변환 실행** → 출력 폴더 선택

### 3. 페이지 작업 (추출/삭제/회전)
1. **페이지** 탭 선택
2. PDF 파일 선택
3. 페이지 범위 입력 (예: `1-3, 5, 7-10`)
4. 작업 선택 (추출/삭제/회전)
5. **실행** → 저장 위치 선택

### 4. 워터마크 추가
1. **보안** 탭 선택
2. PDF 파일 선택
3. 워터마크 텍스트 입력
4. 옵션 설정:
   - 투명도 (0.1 ~ 1.0)
   - 글자 크기
   - 회전 각도
   - 위치 (중앙/타일)
5. **워터마크 적용** 클릭

### 5. PDF 암호화
1. **보안** 탭 선택
2. PDF 파일 선택
3. 비밀번호 입력
4. **암호화 실행** 클릭

### 6. AI 요약 (Gemini API)
1. **AI 요약** 탭 선택
2. API 키 입력 후 **저장** 클릭
3. PDF 파일 선택
4. 언어 선택 (한국어/영어)
5. 요약 스타일 선택 (간결/상세/글머리 기호)
6. **요약 실행** 클릭

### 7. 페이지 순서 변경
1. **순서 변경** 탭 선택
2. PDF 파일 선택 (자동으로 페이지 목록 로드)
3. 페이지를 드래그하여 순서 변경
4. **저장** 클릭

### 8. 배치 처리
1. **배치** 탭 선택
2. 여러 PDF 파일 추가
3. 작업 선택 (압축, 워터마크, 암호화 등)
4. 공통 옵션 설정
5. **배치 실행** 클릭

---

## ⌨️ 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 파일 열기 |
| `Ctrl+Q` | 앱 종료 |
| `Ctrl+T` | 다크/라이트 테마 전환 |
| `Ctrl+Z` | 실행 취소 (Undo) |
| `Ctrl+Y` | 다시 실행 (Redo) |
| `Ctrl+1` | 병합 탭 |
| `Ctrl+2` | 변환 탭 |
| `Ctrl+3` | 페이지 탭 |
| `Ctrl+4` | 보안 탭 |
| `Ctrl+5` | 순서 변경 탭 |
| `Ctrl+6` | 배치 탭 |
| `Ctrl+7` | 고급 탭 |
| `Ctrl+8` | AI 요약 탭 |

---

## 📦 빌드 (PyInstaller)

### 빌드 실행
```bash
pyinstaller pdf_master.spec --clean
```

### 빌드 결과
- 출력: `dist/PDF_Master_v4.5.exe`
- 크기: ~30-40MB (UPX 압축 적용)

### 빌드 최적화
- 불필요한 PyQt6 모듈 제외 (WebEngine, Multimedia, 3D 등)
- UPX 압축 적용
- 단일 실행 파일 생성

---

## 📁 프로젝트 구조

```
pdf-master-main/
├── main.py                    # 애플리케이션 진입점
├── pdf_master.spec            # PyInstaller 빌드 설정
├── README.md                  # 프로젝트 설명서
├── CLAUDE.md                  # Claude AI 가이드
├── GEMINI.md                  # Gemini AI 가이드
└── src/
    ├── core/                  # 핵심 비즈니스 로직
    │   ├── ai_service.py      # Gemini AI 서비스
    │   ├── constants.py       # 전역 상수
    │   ├── i18n.py            # 다국어 지원 (v4.4)
    │   ├── settings.py        # 설정 관리
    │   ├── undo_manager.py    # Undo/Redo 관리
    │   └── worker.py          # PDF 작업 스레드
    └── ui/                              # UI 컴포넌트
        ├── main_window.py               # 메인 윈도우 조립/수명주기
        ├── main_window_config.py        # 앱 상수/AI 가용성
        ├── main_window_core.py          # 메뉴/헤더/테마/단축키
        ├── main_window_preview.py       # 미리보기/최근 파일
        ├── main_window_worker.py        # Worker 연결/오버레이
        ├── main_window_undo.py          # Undo/Redo/백업 정리
        ├── main_window_tabs_basic.py    # 기본 탭 (병합/변환/페이지/보안/순서/배치)
        ├── main_window_tabs_advanced.py # 고급 탭 (편집/추출/마크업/기타)
        ├── main_window_tabs_ai.py       # AI 탭/채팅/키워드/그리드
        ├── progress_overlay.py          # 진행 오버레이
        ├── styles.py                    # 테마/스타일시트
        ├── thumbnail_grid.py            # 썸네일 그리드
        ├── widgets.py                   # 커스텀 위젯
        └── zoomable_preview.py          # 줌/패닝 미리보기
```

---

## 🔧 설정 파일

설정 파일 위치: `~/.pdf_master_settings.json`

```json
{
  "theme": "dark",
  "recent_files": [],
  "last_output_dir": "",
  "window_geometry": "..."
}
```

API 키는 현재 UI 기준으로 설정 파일에 저장되며, `keyring` 사용 가능 시 별도 보관 로직을 지원합니다.

---

## 📝 변경 이력

### v4.5.1 (2026-02-19) - 안정화/호환성 업데이트
- 🛡️ **Worker 사전검증(Preflight) 추가** - 작업 시작 전 입력 파일 존재/크기 검증으로 fail-fast 처리
- 🔁 **Worker 파라미터 양방향 호환** - 신규/구 kwargs 동시 수용 (`draw_shapes`, `add_link`, `insert_textbox`, `copy_page_between_docs`, `image_watermark`)
- 🧭 **고급 기능 오동작 수정** - 도형/링크/텍스트상자/페이지복사/이미지워터마크 UI 전달값이 실제 작업에 반영되도록 보완
- ↩️ **Undo 모드 정합성 수정** - `duplicate_page` 작업의 Undo 등록 누락 수정
- 🖥️ **폴더 열기 호환성 개선** - Linux/macOS에서 Qt `QDesktopServices` 경로 열기 사용
- 🌐 **i18n 로케일 감지 개선** - `locale.getdefaultlocale()` 비권장 경로 제거 (`getlocale + env fallback`)
- ✅ **회귀 테스트 확장** - Worker 파라미터 호환/사전검증/i18n 감지 테스트 추가

### v4.5 (2026-01-22)
- 📐 **도형 그리기** - 사각형, 원, 선 추가 (위치, 크기, 색상 지정)
- 🔗 **하이퍼링크 추가** - URL 링크 또는 페이지 이동 링크 삽입
- 📝 **텍스트 상자** - PDF에 텍스트 직접 삽입 (위치, 폰트, 색상)
- 📋 **페이지 복사** - 다른 PDF에서 특정 페이지 복사해오기
- 🖼️ **이미지 워터마크 개선** - 9개 위치, 크기(px), 투명도(%) 파라미터 지원
- 🖨️ **미리보기 인쇄** - 미리보기 패널에서 바로 인쇄
- 💬 **PDF 채팅** - PDF 내용에 대해 AI에게 질문하기
- 🏷️ **키워드 추출** - AI 기반 핵심 키워드 추출
- 🔒 **AI 스레드 안전성** - AI 싱글톤 Double-check locking 적용
- 🌐 **i18n 확장** - 88개 새 번역 키 추가 + 하드코딩 메시지 제거
- 🧩 **UI 모듈 분리** - `main_window.py`를 믹스인 기반 구조로 분할

### v4.4 (2026-01-16)
- 🌐 **다국어 지원 (i18n)** - 한국어 및 영어 지원 (시스템 언어 자동 감지)
- ⚙️ **언어 설정** - 설정 메뉴에서 언어 변경 가능 (Auto/KO/EN)
- 🔄 **UI 리팩토링** - 모든 텍스트 리소스 외부화 처리

### v4.3 (2026-01-16)
- 🔄 **Undo/Redo 기능** - 페이지 삭제, 회전, 압축 등 실행 취소 지원
- 💾 **종료 시 설정 저장** - 창 위치, 테마 자동 저장
- 🎨 **진행 오버레이** - 작업 중 취소 가능한 풀스크린 다이얼로그

### v4.2 (2026-01-06)
- 🔄 **google-genai SDK** - 새 공식 SDK 사용
- 🧠 **gemini-flash-latest** - 최신 AI 모델
- ❌ **PDF → Word 기능 제거** - 의존성 간소화
- 📦 **빌드 경량화** - ~30-40MB

---

## 🧪 테스트 현황 (v4.5.1)

- 신규 테스트:
  - `tests/test_worker_param_compat.py` (고급 기능 kwargs 호환 검증)
  - `tests/test_worker_preflight.py` (실행 전 입력 검증 fail-fast 검증)
  - `tests/test_i18n.py` (시스템 언어 감지 경로 검증)
- 기존 테스트와 함께 `pytest -q` 통과 기준으로 유지합니다.

---

## ⚠️ 알려진 제한사항

1. **AI 요약**: 최대 30,000자 텍스트 제한
2. **렌더링**: 최대 8000px 해상도 제한
3. **암호화된 PDF**: 일부 작업에서 복호화 필요
4. **대용량 파일**: 2GB 이상 처리 불가

---

## 🤝 기여

버그 리포트, 기능 제안, PR 환영합니다!

---

## 📄 라이선스

MIT License

Copyright (c) 2026 PDF Master

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
