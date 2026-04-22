from .en import TRANSLATIONS as EN_TRANSLATIONS
from .ko import TRANSLATIONS as KO_TRANSLATIONS

TRANSLATIONS = {
    "ko": KO_TRANSLATIONS,
    "en": EN_TRANSLATIONS,
}

TRANSLATIONS["ko"].update(
    {
        "msg_summary_save_failed": "요약 저장에 실패했습니다.",
        "ai_meta_file_api": "AI 상태: Gemini File API 사용",
        "ai_meta_file_api_page_focus": "AI 상태: Gemini File API 사용, 처음 {}페이지 중심",
        "ai_meta_text_fallback": "AI 상태: 로컬 텍스트 fallback 사용 ({} / {}페이지)",
        "ai_meta_text_fallback_truncated": "AI 상태: 로컬 텍스트 fallback 사용, {} / {}페이지, {}자 제한으로 잘림",
        "ai_meta_saved_header": "[AI 처리 메타] {}",
        "title_api_key_plaintext_confirm": "평문 저장 확인",
        "msg_api_key_plaintext_confirm": "보안 저장소에 API 키를 저장할 수 없습니다.\n설정 파일에 평문으로 저장할까요?",
        "msg_api_key_saved_plaintext": "API 키가 설정 파일에 평문 저장되었습니다.",
        "msg_api_key_plaintext_declined": "API 키를 저장하지 않았습니다.",
        "msg_undo_unavailable": "이번 작업은 Undo를 사용할 수 없습니다.",
        "visual_diff_legend_removed": "빨강: file1에만 있음",
        "visual_diff_legend_added": "파랑: file2에만 있음",
    }
)

TRANSLATIONS["en"].update(
    {
        "msg_summary_save_failed": "Failed to save summary.",
        "ai_meta_file_api": "AI status: Gemini File API",
        "ai_meta_file_api_page_focus": "AI status: Gemini File API, focusing on the first {} page(s)",
        "ai_meta_text_fallback": "AI status: local text fallback ({} / {} pages)",
        "ai_meta_text_fallback_truncated": "AI status: local text fallback, {} / {} pages, truncated at {} chars",
        "ai_meta_saved_header": "[AI processing meta] {}",
        "title_api_key_plaintext_confirm": "Confirm plaintext save",
        "msg_api_key_plaintext_confirm": "The API key could not be saved to secure storage.\nSave it in plaintext in the settings file?",
        "msg_api_key_saved_plaintext": "API key was saved in plaintext to the settings file.",
        "msg_api_key_plaintext_declined": "The API key was not saved.",
        "msg_undo_unavailable": "Undo is unavailable for this run.",
        "visual_diff_legend_removed": "Red: only in file1",
        "visual_diff_legend_added": "Blue: only in file2",
    }
)

__all__ = ["EN_TRANSLATIONS", "KO_TRANSLATIONS", "TRANSLATIONS"]
