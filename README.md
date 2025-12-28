# 📑 PDF Master v2.9

**모든 PDF 작업을 한 곳에서** - 초보자도 쉽게 사용할 수 있는 올인원 PDF 도구.
강력한 기능과 직관적인 UI, 그리고 모듈화된 구조로 새롭게 태어났습니다.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.23+-orange)

---

## ✨ 주요 기능

| 탭 | 기능 |
|----|------|
| 📎 **병합** | 여러 PDF를 하나로 합치기 (폴더 드롭, 파일 개수 표시) |
| 🔄 **변환** | PDF→이미지 (프리셋), 이미지→PDF, 텍스트 추출 |
| ✂️ **페이지** | 페이지 추출, 삭제, 회전 |
| 🔒 **편집/보안** | 메타데이터 수정, 워터마크, 암호화, 압축 |
| 🔀 **페이지 순서** | 드래그 앤 드롭으로 순서 변경 |
| 📦 **일괄 처리** | 폴더 전체 PDF에 일괄 적용 |
| 🔧 **고급 기능** | 분할, 번호, 스탬프, 여백, 링크, 양식, 비교, 정보, 복제, 역순, 크기변경, 이미지 추출, 전자서명, **북마크, 검색, 하이라이트** |

---

## 🆕 v2.9 신규 기능

| 기능 | 설명 |
|------|------|
| � **북마크 추출** | PDF 목차/북마크 구조 추출 |
| � **텍스트 검색** | PDF 내 텍스트 검색 및 위치 확인 |
| �️ **하이라이트** | 검색어 자동 하이라이트 표시 |

---

## 🖥️ UI/UX 특징

- 🎨 **모던 테마** (Dark/Light, Ctrl+T 전환)
- 👁️ **실시간 미리보기** (페이지 네비게이션)
- 📂 **드래그 앤 드롭** 파일 및 폴더 지원
- 🍞 **Toast 알림** 비차단형 알림
- 📊 **HiDPI 지원** 고해상도 최적화
- 💾 **윈도우 위치 저장** 앱 종료/시작 시 복원

---

## 🚀 실행 방법

### 필수
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

## ⌨️ 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl + O` | 파일 열기 |
| `Ctrl + Q` | 프로그램 종료 |
| `Ctrl + T` | 테마 전환 |
| `Ctrl + 1~4` | 탭 전환 |
| `F1` | 도움말 |

---

## 📦 빌드

```bash
pyinstaller pdf_master.spec
```

**결과물:** `dist/PDF_Master_v2.9.exe`

---

## 📁 프로젝트 구조

```
pdf-master/
├── main.py                 # 진입점 (HiDPI)
├── src/
│   ├── core/
│   │   ├── worker.py       # PDF 처리 (885줄, 30+ 기능)
│   │   └── settings.py     # 설정 관리
│   └── ui/
│       ├── main_window.py  # 메인 윈도우 (1817줄)
│       ├── widgets.py      # 커스텀 위젯
│       └── styles.py       # 스타일시트
├── pdf_master.spec         # PyInstaller
└── README.md
```

---

## 📋 변경 이력

### v2.9 (Latest)
- ✅ 북마크/목차 추출
- ✅ 텍스트 검색
- ✅ 텍스트 하이라이트

### v2.8
- PDF 정보/통계, 페이지 복제/역순, 크기 변경, 이미지 추출, 전자 서명

### v2.7
- 파일 개수 표시, 윈도우 위치 저장, Ctrl+T, 삭제 확인

### v2.6
- 폴더 드롭, 프리셋, 링크 추출, 양식 작성, PDF 비교

---

**Made with ❤️ using Python & PyQt6**
