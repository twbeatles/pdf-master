from __future__ import annotations


def default_settings() -> dict:
    """
    기본 설정 생성.

    NOTE: list/dict 같은 mutable 기본값이 호출 간 공유되지 않도록
    매 호출마다 새 객체를 생성합니다.
    """
    return {
        "theme": "dark",
        "recent_files": [],
        "last_output_dir": "",
        "splitter_sizes": None,
        "window_geometry": None,
        "language": "auto",  # auto, ko, en
        "preview_search_expanded": True,
        "preview_focus_mode": False,
        "splitter_sizes_before_focus": None,
        "chat_histories": {},
        # 채팅 기록 설정 파일 저장 (False면 세션 메모리만)
        "save_chat_histories": True,
        # 작업 완료 알림: dialog(toast+모달) | toast(토스트만)
        "notify_mode": "dialog",
        # Worker 취소 시 대기 큐 폐기
        "clear_pending_on_cancel": True,
        # gemini_api_key는 keyring 미사용 시에만 파일에 저장됨
    }
