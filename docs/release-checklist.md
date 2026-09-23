# Release & Update Checklist

> PROJECT_AUDIT.md §5 Confirmed Gap 대응 — 매니페스트 만료 정책 문서화.
> 자동 업데이트 전체 흐름의 기술 SSOT는 `PROJECT_AUDIT.md` §2, 사용자 안내는
> `README.md`/`README_EN.md`의 업데이트 절이다.

## 1. 릴리스 전

- [ ] `src/core/_constants_impl/values.py`의 `VERSION`을 새 버전으로 갱신
      (EXE명·패키지 메타데이터·매니페스트 URL은 이 단일 소스를 추종).
- [ ] `vX.Y.Z` 태그로 푸시하거나 Release workflow의 `version` 입력 사용.
- [ ] GitHub Actions secrets 확인: `PM_UPDATE_PRIVATE_KEY_B64`,
      `PM_UPDATE_PUBLIC_KEY_B64` (개인키는 절대 커밋 금지).
- [ ] 서명 공개키가 `src/core/constants.py`의 `UPDATE_PUBLIC_KEY_B64`와 일치하는지 확인
      (불일치 시 `scripts/build_update_manifest.py`가 실패한다).

## 2. 매니페스트 만료 정책 (365일)

- 서명 매니페스트(`updates/latest.json`)의 기본 유효기간은 **발행 후 365일**
  (`scripts/build_update_manifest.py --expires-days`, 기본값 365).
- 앱은 만료된 매니페스트를 `Manifest is expired`로 거부하고 업데이트 실패로 표시한다.
- 매니페스트 만료 **30일 전부터** 업데이트 제안 대화상자에 만료 임박 경고가 표시된다
  (`src/core/update_manifest.py: MANIFEST_EXPIRY_WARN_DAYS`).
- **1년 이상 릴리스가 없으면 정상 앱도 업데이트를 실패**하므로, 만료 전 반드시
  새 릴리스를 게시해 매니페스트를 재발행한다 (코드 변경이 없어도 릴리스만으로 갱신됨).
- 유효기간 조정 시: `--expires-days N`으로 빌드하고, 이 체크리스트와 README 업데이트 절의
  일수를 함께 갱신한다.

## 3. 게시 경쟁·재시도

- `Publish update manifest` 단계는 `pull --rebase + push`를 **최대 3회**
  (지수 백오프 5s·10s) 재시도한다. 그래도 실패하면 workflow를 재실행한다.
- Release 에셋은 존재하는데 `updates/latest.json`이 이전 버전에 머물러 있으면
  게시 경쟁 실패를 의심하고 해당 workflow 실행 로그를 확인한다.

## 4. 클라이언트 동작 (참고)

- 시작 2초 후 자동 확인 1회 + 도움말 메뉴 수동 확인. 자동 확인 실패는 상태바 힌트만
  표시하고, 5분 후 1회 자동 재시도한다. 수동 확인은 실패 원인을 대화상자로 표시한다.
- 다운로드는 일시 네트워크 오류에 한해 **최대 3회**(지수 백오프) 재시도하며,
  크기·SHA-256 검증 실패 시 잔여 스테이징 파일을 정리한다.
- 자동 업데이트는 **Windows 빌드 전용**이다. 다른 플랫폼에서는 릴리스 페이지에서
  직접 다운로드한다.

## 5. 릴리즈 게이트 — 수동 업데이트 E2E (PROJECT_AUDIT.md Phase 2.3)

> stage→교체→smoke→재기동의 자동 E2E는 CI에 편입되어 있지 않으므로,
> 릴리스마다 테스트 PC에서 아래 수동 게이트를 통과한다.

- [ ] 이전 버전 EXE가 설치된 테스트 PC에서 도움말 → 업데이트 확인 → 새 버전 제안 확인.
- [ ] 다운로드→무결성 검증→종료→교체→smoke→재기동까지 자동 진행 확인.
- [ ] `LOCALAPPDATA/PDFMaster/updates/last-update-result.json` 1회 소비·표시 확인
      (다음 기동 시 잔여 결과 없음).
- [ ] (분기별 1회) 고의 실패 롤백: 스테이징 EXE를 손상시킨 뒤 적용 시도 →
      이전 EXE로 복구 + `rolled_back` 결과 확인.
- [ ] 게이트 실패 시 태그를 삭제하지 말고 원인 수정 후 다음 패치 버전으로 재릴리스한다.
