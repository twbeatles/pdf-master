# PDF Master v4.2

📑 **올인원 PDF 편집 프로그램** - PyQt6 기반 데스크톱 앱

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ 주요 기능

### 📄 기본 기능
- **PDF 병합** - 여러 PDF를 하나로 합치기 (드래그 앤 드롭)
- **PDF → 이미지** - PNG/JPG/WEBP 변환 (DPI 설정 가능)
- **이미지 → PDF** - 여러 이미지를 PDF로 합치기
- **텍스트 추출** - PDF에서 텍스트 추출 (TXT 저장)

### ✂️ 페이지 편집
- **페이지 번호 삽입** - 위치/형식/폰트 커스텀
- **페이지 추출/삭제/회전**
- **페이지 순서 변경** - 드래그 앤 드롭
- **페이지 썸네일 그리드** - 모든 페이지 한눈에 보기

### 🔒 보안 & 편집
- **암호화/복호화** - AES-256 보안
- **워터마크** - 텍스트/타일 (전경/배경 선택)
- **스탬프 추가** - 기밀, 승인됨, 사본 등
- **메타데이터 편집** - 제목, 저자, 키워드 등

### 🔧 고급 기능
- **PDF 분할** - 각 페이지별/범위별
- **PDF 압축** - 파일 크기 최적화
- **테이블 추출** - CSV 저장
- **주석/하이라이트** - 텍스트 마크업

### 🤖 AI 기능
- **AI 기반 PDF 요약** - Gemini API 연동 (`gemini-flash-latest` 모델)

### 🎨 UI/UX
- **Premium 테마** - 모던 그라데이션, 글래스모피즘
- **Undo/Redo** - Ctrl+Z/Y 단축키
- **미리보기 줌/패닝** - 마우스 휠 줌, 드래그 이동

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
# 기본 설치
pip install PyQt6 PyMuPDF

# AI 기능 (선택)
pip install google-genai
```

### 실행
```bash
python main.py
```

---

## 📦 빌드 (PyInstaller)

```bash
# 경량화 빌드
pyinstaller pdf_master.spec --clean
```

빌드 결과: `dist/PDF_Master_v4.2.exe` (~30-40MB)

---

## ⌨️ 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 파일 열기 |
| `Ctrl+Q` | 종료 |
| `Ctrl+T` | 테마 전환 |
| `Ctrl+Z` | 실행 취소 |
| `Ctrl+Y` | 다시 실행 |
| `Ctrl+1~8` | 탭 전환 |

---

## 📝 변경 이력

### v4.2 (2026-01-06)
- 🔄 **google-genai SDK** - 새 공식 SDK 사용
- 🧠 **gemini-flash-latest** - 최신 AI 모델
- ❌ **PDF → Word 기능 제거** - 의존성 간소화
- 🐛 **리소스 관리 개선** - PDF 핸들 누수 수정
- 📦 **빌드 경량화** - ~30-40MB

---

## 📄 라이선스

MIT License
