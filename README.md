# 📑 PDF Master v2.6

**모든 PDF 작업을 한 곳에서** - 초보자도 쉽게 사용할 수 있는 올인원 PDF 도구.
강력한 기능과 직관적인 UI, 그리고 모듈화된 구조로 새롭게 태어났습니다.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.23+-orange)

---

## ✨ 주요 기능

| 탭 | 기능 |
|----|------|
| 📎 **병합** | 여러 PDF를 하나로 합치기 (드래그 앤 드롭, 폴더 드롭 지원) |
| 🔄 **변환** | PDF→이미지 (프리셋 저장), 이미지→PDF, 텍스트 추출 |
| ✂️ **페이지** | 페이지 추출, 삭제, 회전 |
| 🔒 **편집/보안** | 메타데이터 수정, 워터마크, 암호화, 압축 |
| 🔀 **페이지 순서** | 드래그 앤 드롭으로 페이지 순서 변경 |
| 📦 **일괄 처리** | 폴더 전체 PDF에 워터마크/암호화/회전 일괄 적용 |
| 🔧 **고급 기능** | 분할, 페이지 번호, 스탬프, 여백 자르기, 빈 페이지, **링크 추출, 양식 작성, PDF 비교** |

---

## 🆕 v2.6 신규 기능

| 기능 | 설명 |
|------|------|
| 📂 **폴더 드롭** | 폴더를 드래그하면 내부 PDF 모두 자동 추가 |
| 💾 **프리셋 저장** | 이미지 변환 설정 (포맷, DPI) 저장/로드 |
| 🖨️ **직접 인쇄** | PDF 처리 후 바로 프린터 출력 |
| 🔗 **링크 추출** | PDF 내 모든 URL 추출하여 텍스트 파일로 저장 |
| 📝 **양식 작성** | PDF 양식 필드 감지 → 값 입력 → 저장 |
| 🔍 **PDF 비교** | 두 PDF 문서 비교하여 차이점 분석 |

---

## 🖥️ UI/UX 특징

- 🎨 **모던 테마** (Dark/Light 모드 자동 동기화)
- 👁️ **실시간 미리보기** (페이지 네비게이션 포함)
- 📂 **드래그 앤 드롭** 파일 및 **폴더** 완벽 지원
- 🍞 **Toast 알림** 비차단형 알림
- 📊 **HiDPI 지원** 고해상도 디스플레이 최적화
- 🔲 **메뉴 바** 파일/도움말 메뉴 지원

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

## ⌨️ 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl + O` | 파일 열기 |
| `Ctrl + Q` | 프로그램 종료 |
| `Ctrl + 1~4` | 탭 전환 |
| `F1` | 도움말 표시 |

---

## 📦 빌드

```bash
pyinstaller pdf_master.spec
```

**결과물:** `dist/PDF_Master_v2.6.exe`

---

## 📁 프로젝트 구조

```
pdf-master/
├── main.py                 # 프로그램 진입점 (HiDPI 지원)
├── src/
│   ├── core/
│   │   ├── worker.py       # PDF 처리 (링크추출, 양식, 비교 포함)
│   │   └── settings.py     # 설정 관리
│   └── ui/
│       ├── main_window.py  # 메인 윈도우
│       ├── widgets.py      # ToastWidget, FileListWidget 등
│       └── styles.py       # 스타일시트
├── pdf_master.spec         # PyInstaller 빌드 설정
└── README.md
```

---

## 📋 변경 이력

### v2.6 (Latest)
- ✅ **폴더 드래그 앤 드롭**: 폴더 드롭 시 내부 PDF 자동 추가
- ✅ **내보내기 프리셋**: 이미지 변환 설정 저장/로드
- ✅ **링크 추출**: PDF 내 모든 URL 추출
- ✅ **양식 작성기**: PDF 양식 필드 감지 및 채우기
- ✅ **PDF 비교**: 두 문서 텍스트 비교

### v2.5
- Toast 알림, HiDPI, 메뉴 바 추가

### v2.4.1
- 미리보기 안정화, 모듈 분리

---

**Made with ❤️ using Python & PyQt6**
