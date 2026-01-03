# PDF Master v3.1

📑 **올인원 PDF 편집 프로그램** - PyQt6 기반 데스크톱 앱

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ 주요 기능

### 📄 기본 기능
- **PDF 병합** - 여러 PDF를 하나로 합치기
- **PDF → 이미지** - PNG/JPG/WEBP 변환 (DPI 설정)
- **텍스트 추출** - PDF에서 텍스트 추출

### ✂️ 페이지 편집
- **페이지 번호 삽입** - 위치/형식 커스텀
- **페이지 추출/삭제/회전**
- **페이지 순서 변경** - 드래그 앤 드롭

### 🔒 보안 & 편집
- **암호화/복호화** - AES-256
- **워터마크** - 텍스트/이미지
- **메타데이터 편집**
- **PDF 압축** - 파일 크기 최적화

### 🔧 고급 기능
- **PDF 분할** - 각 페이지별/범위별
- **스탬프 추가** - 기밀, 승인됨 등
- **테이블 추출** - CSV 저장
- **주석/하이라이트** - 텍스트 마크업

---

## 🚀 설치 및 실행

### 요구 사항
```
Python 3.10+
PyQt6
PyMuPDF (fitz)
```

### 설치
```bash
pip install -r requirements.txt
```

### 실행
```bash
python main.py
```

---

## ⌨️ 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 파일 열기 |
| `Ctrl+Q` | 종료 |
| `Ctrl+T` | 테마 전환 |
| `Ctrl+1~7` | 탭 전환 |
| `F1` | 도움말 |

---

## 🏗️ 빌드

### PyInstaller 빌드
```bash
pyinstaller pdf_master.spec
```

빌드 결과: `dist/PDF_Master.exe`

---

## 📁 프로젝트 구조

```
pdf-master-main/
├── main.py              # 엔트리포인트
├── src/
│   ├── core/
│   │   ├── worker.py    # PDF 작업 스레드
│   │   └── settings.py  # 설정 관리
│   └── ui/
│       ├── main_window.py  # 메인 윈도우
│       ├── widgets.py      # 커스텀 위젯
│       └── styles.py       # 테마/스타일
└── pdf_master.spec      # PyInstaller 빌드
```

---

## 📝 변경 이력

### v3.1 (2026-01-03)
- 🐛 8개 버그 수정 (메모리 누수, division by zero 등)
- 🎨 UI 테마 통일 (파란색 액센트)
- ⌨️ 단축키 Ctrl+5~7 추가
- 📍 페이지 번호 기능 → 페이지 탭 이동

### v3.0
- 7개 탭 구조 (병합/변환/페이지/순서/편집/일괄/고급)
- 실시간 미리보기 패널
- 다크/라이트 테마

---

## 📄 라이선스

MIT License
