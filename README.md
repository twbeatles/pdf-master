# 📑 PDF Master v2.2

**모든 PDF 작업을 한 곳에서** - 초보자도 쉽게 사용할 수 있는 올인원 PDF 도구

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-PDF%20Engine-orange)
![Windows](https://img.shields.io/badge/Windows-10%2F11-blue)

---

## ✨ 주요 기능

### 📎 PDF 병합
- 여러 PDF 파일을 하나로 합치기
- **드래그 앤 드롭**으로 파일 추가
- 순서 변경 가능 (드래그로 재정렬)

### 🔄 변환
- **PDF → 이미지** (PNG, JPG / DPI 조절)
- **이미지 → PDF** (여러 이미지를 하나의 PDF로)
- **텍스트 추출** (.txt 저장)

### ✂️ 페이지 관리
- 특정 페이지 **추출** (예: 1-3, 5, 8)
- 특정 페이지 **삭제**
- 페이지 **회전** (90°, 180°, 270°)

### 🔀 페이지 순서 변경 ⭐NEW
- PDF 페이지 목록 표시
- **드래그**로 페이지 순서 변경
- **역순 정렬** 버튼

### 🔒 편집 & 보안
- **메타데이터** 수정 (제목, 작성자, 주제)
- **워터마크** 삽입 (텍스트, 색상 선택)
- **암호화** (AES-256)
- **압축** (용량 최적화)
- **암호화된 PDF 자동 감지** - 비밀번호 입력 다이얼로그

### 📦 일괄 처리 ⭐NEW
- 폴더 전체 PDF에 동일 작업 일괄 적용
- 지원 작업: 압축, 워터마크, 암호화, 회전

---

## 🖥️ UI/UX 특징

- 🎨 **다크/라이트 테마** 전환 (설정 자동 저장)
- 📁 **드래그 앤 드롭** 지원 (모든 파일 선택 영역)
- 👁️ **실시간 미리보기** 패널
- 📋 **최근 파일 메뉴** (빠른 접근)
- 📂 **작업 후 폴더 열기** 버튼
- 📏 **패널 크기 조절** (드래그로 조절, 설정 저장)
- 📝 **단계별 가이드** (1️⃣, 2️⃣, 3️⃣)

---

## ⌨️ 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+O` | 파일 열기 |
| `Ctrl+Q` | 프로그램 종료 |
| `F1` | 도움말 |
| `Ctrl+1` | 병합 탭 |
| `Ctrl+2` | 변환 탭 |
| `Ctrl+3` | 페이지 탭 |
| `Ctrl+4` | 순서 탭 |
| `Ctrl+5` | 편집/보안 탭 |
| `Ctrl+6` | 일괄 탭 |

---

## 🚀 설치 및 실행

### 필수 요구사항
- Python 3.9 이상
- Windows 10/11

### 의존성 설치
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
- `dist/PDF_Master_v2.exe` (단일 실행 파일, 약 40MB)

---

## 📁 파일 구조

```
pdf-master/
├── pdf-master-v2.py    # 메인 프로그램 (~1500 lines)
├── pdf_master.spec     # PyInstaller 빌드 설정
└── README.md           # 설명서
```

---

## 💻 기술 스택

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| PyQt6 | 6.4+ | GUI 프레임워크 |
| PyMuPDF (fitz) | 1.23+ | PDF 처리 엔진 |

---

## 📋 v2.2 변경사항

- ✅ PDF 암호 해제 다이얼로그 추가
- ✅ 최근 파일 메뉴 (📋 버튼)
- ✅ 페이지 순서 변경 탭
- ✅ 일괄 처리 탭 (폴더 전체 PDF)
- ✅ UI 레이아웃 개선 (컴팩트한 상태바)
- ✅ 미리보기 메모리 누수 수정
- ✅ 패널 크기 조절 기능 및 설정 저장

---

## 📜 라이센스

MIT License

---

**Made with ❤️ using Python & PyQt6**
