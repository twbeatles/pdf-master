# 📑 PDF Master v2.4 (Refactored)

**모든 PDF 작업을 한 곳에서** - 초보자도 쉽게 사용할 수 있는 올인원 PDF 도구.
강력한 기능과 직관적인 UI, 그리고 모듈화된 구조로 새롭게 태어났습니다.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.23+-orange)

---

## ✨ 주요 기능

| 탭 | 기능 |
|----|------|
| 📎 **병합** | 여러 PDF를 하나로 합치기 (드래그 앤 드롭, 순서 조정) |
| 🔄 **변환** | PDF→이미지 (다중 파일), 이미지→PDF, 텍스트 추출 |
| ✂️ **페이지** | 페이지 추출, 삭제, 회전 |
| 🔒 **편집/보안** | 메타데이터 수정, 워터마크, 암호화, 압축 |
| 🔀 **페이지 순서** | 드래그 앤 드롭으로 페이지 순서 변경, 역순 정렬 |
| 📦 **일괄 처리** | 폴더 전체 PDF에 대해 워터마크/암호화/회전 등 일괄 적용 |
| 🔧 **고급 기능** | PDF 분할, 페이지 번호 삽입, 스탬프, 여백 자르기, 빈 페이지 삽입 |

---

## 🖥️ UI/UX 특징

- 🎨 **모던 테마** (Dark/Light 모드 자동 동기화)
- 👁️ **실시간 미리보기** (페이지 네비게이션 포함)
- 📂 **드래그 앤 드롭** 완벽 지원 (파일 목록, 드롭존)
- ⚙️ **사용자 친화적** (휠 스크롤 방지, 최근 파일 메뉴)

---

## 🚀 실행 방법

### 필수 요구사항
```
Python 3.9+
PyQt6
PyMuPDF (fitz)
```

### 설치
```bash
pip install PyQt6 PyMuPDF
```

### 실행
```bash
python main.py
```

---

## 📦 빌드 (배포용 실행 파일 생성)

이 프로젝트는 `PyInstaller`를 사용하여 단일 실행 파일로 배포할 수 있습니다.
최적화된 `.spec` 파일이 포함되어 있습니다.

```bash
pyinstaller pdf_master.spec
```

**결과물:** `dist/PDF_Master_v2.4.exe`

---

## 📁 프로젝트 구조 (Refactored)

```
pdf-master/
├── main.py                 # 프로그램 진입점 (Entry Point)
├── src/
│   ├── core/               # 핵심 로직
│   │   ├── worker.py       # PDF 처리 워커 스레드
│   │   └── settings.py     # 설정 관리
│   └── ui/                 # UI 모듈
│       ├── main_window.py  # 메인 윈도우 클래스 (Tabs, Actions)
│       ├── widgets.py      # 커스텀 위젯 (DropZone, FileList)
│       └── styles.py       # 스타일시트 정의
├── pdf_master.spec         # PyInstaller 빌드 설정
└── README.md               # 설명서
```

---

## 📋 변경 이력 (v2.4)

### v2.4.1 (Latest Fixes)
- ✅ **미리보기 안정화**: 모든 탭에서 파일 선택 시 미리보기 연결 (병합/일괄 탭 포함)
- ✅ **구조 개선**: `src/core`, `src/ui`로 모듈 분리
- ✅ **빌드 최적화**: `.spec` 파일 개선으로 용량 최적화
- ✅ **버그 수정**: `UnboundLocalError` 및 변수명 충돌 해결

---

**Made with ❤️ using Python & PyQt6**
