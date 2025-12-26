# 📑 PDF Master v2.4

**모든 PDF 작업을 한 곳에서** - 초보자도 쉽게 사용할 수 있는 올인원 PDF 도구

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.23+-orange)

---

## ✨ 주요 기능

| 탭 | 기능 |
|----|------|
| 📎 **병합** | 여러 PDF를 하나로 합치기 (드래그 앤 드롭) |
| 🔄 **변환** | PDF→이미지 (다중 파일), 이미지→PDF, 텍스트 추출 (다중 파일) |
| ✂️ **페이지** | 추출, 삭제, 회전 |
| 🔀 **순서** | 드래그로 페이지 순서 변경, 역순 정렬 |
| 🔒 **편집/보안** | 메타데이터, 워터마크, 암호화, 압축 |
| 📦 **일괄** | 폴더 전체 PDF 일괄 처리 |
| 🔧 **고급** | PDF 분할, 페이지 번호, 스탬프, 여백 자르기, 빈 페이지 |

---

## 🖥️ UI/UX 특징

- 🎨 **다크/라이트 테마** 전환 (자동 동기화)
- 👁️ **미리보기 페이지 네비게이션** (PREV/NEXT)
- 📋 **최근 파일 메뉴** (최대 10개)
- 📂 **드래그 앤 드롭** 지원
- 🔄 **다중 파일 일괄 변환** (PDF→이미지, 텍스트 추출)
- 🚫 **휠 스크롤 값 변경 방지** (UX 개선)

---

## 🔢 페이지 번호 형식

| 형식 | 예시 |
|------|------|
| `{n} / {total}` | 1 / 10 |
| `Page {n} of {total}` | Page 1 of 10 |
| `- {n} -` | - 1 - |
| `페이지 {n}` | 페이지 1 |

---

## ⌨️ 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 파일 열기 |
| `Ctrl+Q` | 종료 |
| `F1` | 도움말 |
| `Ctrl+1~7` | 탭 전환 |

---

## 🚀 설치 및 실행

### 필수 요구사항
```
Python 3.9+
PyQt6
PyMuPDF
```

### 설치
```bash
pip install PyQt6 PyMuPDF
```

### 실행
```bash
python pdf-master-v2.py
```

---

## 📦 배포 (PyInstaller)

### 빌드
```bash
pyinstaller pdf_master.spec
```

### 결과
- `dist/PDF_Master_v2.4.exe` (약 25-35MB)

---

## 📁 파일 구조
```
pdf-master/
├── pdf-master-v2.py    # 메인 프로그램 (~2000줄)
├── pdf_master.spec     # PyInstaller 빌드 설정
└── README.md           # 설명서
```

---

## 📋 변경 이력

### v2.4
- ✅ PDF→이미지 다중 파일 일괄 변환
- ✅ 텍스트 추출 다중 파일 지원
- ✅ 페이지 번호 형식 드롭다운 및 안내
- ✅ 미리보기 페이지 네비게이션 (PREV/NEXT)
- ✅ 휠 스크롤 값 변경 방지
- ✅ 라이트 모드 완전 지원
- ✅ 테마 동기화 개선

### v2.3
- 고급 기능 탭 (분할, 스탬프, 자르기 등)

### v2.2
- 페이지 순서 변경, 일괄 처리 탭

---

**Made with ❤️ using Python & PyQt6**
