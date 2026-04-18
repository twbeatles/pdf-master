from __future__ import annotations


FALLBACK_MESSAGES = {
    "err_ai_module_not_found": "AI 서비스 모듈을 찾을 수 없습니다.",
    "err_pdf_not_found": "PDF 파일을 찾을 수 없습니다.",
    "err_api_key_required": "Gemini API 키가 필요합니다.",
    "err_ai_unavailable": "AI 서비스를 사용할 수 없습니다.",
    "err_question_required": "질문을 입력해주세요.",
    "err_input_file_missing": "입력 파일이 존재하지 않습니다.",
    "err_output_path_missing": "출력 경로가 지정되지 않았습니다.",
    "err_required_parameter_missing": "필수 옵션이 누락되었습니다: {}",
    "err_cancelled": "작업이 취소되었습니다.",
    "err_pdf_corrupted": "PDF 파일이 손상되었거나 형식이 올바르지 않습니다.",
    "err_operation_failed": "오류 발생: {}",
    "err_file_access_denied": "파일 접근 권한이 없습니다: {}",
    "err_invalid_markup_type": "지원하지 않는 마크업 유형입니다: {}",
    "err_page_out_of_range": "페이지 번호 오류: {} (전체 {}페이지)",
    "err_pdf_has_no_pages": "PDF에 페이지가 없습니다.",
    "err_invalid_page_range": "유효한 페이지 범위가 아닙니다: {}",
    "err_copy_pages_required": "복사할 페이지 범위를 입력해주세요.",
    "err_link_target_zero_based": "대상 페이지 번호 오류(0-based): {} (허용: 0~{})",
    "err_page_number_numeric": "페이지 번호는 숫자여야 합니다: {}",
    "err_attachment_path_invalid": "첨부 파일 경로가 유효하지 않습니다: {}",
}


def get_message(key: str, *args: object) -> str:
    """v4.5: i18n 메시지 헬퍼 - 폴백 지원."""
    manager = None
    try:
        from ..i18n import tm

        manager = tm
    except ImportError:
        manager = None

    if manager:
        return manager.get(key, *args)

    msg = FALLBACK_MESSAGES.get(key, key)
    if args:
        try:
            return msg.format(*args)
        except (IndexError, KeyError):
            return msg
    return msg
