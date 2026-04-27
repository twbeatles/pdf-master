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
    "err_wrong_password": "❌ 비밀번호가 틀렸습니다.",
    "err_password_required": "비밀번호를 입력해주세요.",
    "err_watermark_text_required": "워터마크 텍스트가 없습니다.",
    "err_split_ranges_required": "분할할 범위가 지정되지 않았습니다.",
    "err_split_no_valid_ranges": "유효한 페이지 범위가 없습니다.",
    "err_target_page_invalid": "대상 페이지 번호가 유효하지 않습니다: {}",
    "err_source_page_invalid": "소스 페이지 번호가 유효하지 않습니다: {}",
    "err_shapes_required": "도형 데이터가 없습니다.",
    "err_link_target_required": "링크 대상이 지정되지 않았습니다.",
    "err_redact_text_required": "삭제할 텍스트가 입력되지 않았습니다.",
    "err_ink_points_required": "좌표 포인트가 2개 이상 필요합니다.",
    "err_no_valid_strokes": "유효한 획이 없습니다.",
    "msg_pages_extracted": "✅ 추출 완료!\n{}페이지 추출됨",
    "msg_pages_deleted": "✅ 삭제 완료!\n{}페이지 삭제됨",
    "msg_pages_rotated": "✅ 회전 완료!\n{}페이지 회전됨 ({}°)",
    "msg_watermark_applied": "✅ 워터마크 적용 완료! ({}, {}%)",
    "msg_layer_background": "배경",
    "msg_layer_foreground": "전경",
    "msg_metadata_saved": "✅ 메타데이터 저장 완료!",
    "msg_encryption_success": "✅ 암호화 완료!",
    "msg_compression_done": "✅ 압축 완료 ({})\n{}KB -> {}KB ({:.1f}% 감소)",
    "msg_images_to_pdf_done": "✅ 이미지 → PDF 변환 완료!\n{}개 이미지 → 1개 PDF",
    "msg_reorder_done": "✅ 페이지 순서 변경 완료!\n{}페이지 재정렬됨",
    "msg_split_done": "✅ PDF 분할 완료!\n{}개 파일 생성됨",
    "msg_page_number_format_roman": "로마 숫자",
    "msg_page_number_format_arabic": "아라비아 숫자",
    "msg_page_numbers_done": "✅ 페이지 번호 삽입 완료! ({})\n{}페이지",
    "msg_blank_page_inserted": "✅ 빈 페이지 삽입 완료!\n위치: {}페이지",
    "msg_page_replaced": "✅ 페이지 교체 완료!",
    "msg_image_watermark_done": "✅ 이미지 워터마크 완료! ({}x{}, {}%)",
    "msg_crop_done": "✅ PDF 자르기 완료!",
    "msg_stamp_done": "✅ 스탬프 추가 완료!",
    "msg_links_extracted": "✅ 링크 추출 완료!\n{}개 링크 발견",
    "msg_form_fields_done": "✅ 양식 필드 감지 완료!\n{}개 필드 발견",
    "msg_form_filled": "✅ 양식 작성 완료!\n{}개 필드 채움",
    "msg_page_duplicated": "✅ 페이지 복제 완료!\n{}페이지를 {}번 복제",
    "msg_reverse_done_single": "✅ 역순 정렬 완료!\n1페이지 (변경 없음)",
    "msg_reverse_done": "✅ 역순 정렬 완료!\n{}페이지",
    "msg_dedup_removed_suffix": " (중복 제거)",
    "msg_images_extracted": "✅ 이미지 추출 완료!{}\n{}개 이미지 저장됨",
    "msg_signature_signer_suffix": " (서명자: {})",
    "msg_signature_timestamp_suffix": " +타임스탬프",
    "msg_signature_inserted": "✅ 전자 서명 삽입 완료!{}\n{}페이지",
    "msg_highlight_done": "✅ 하이라이트 완료!\n'{}': {}개 표시",
    "msg_shapes_added": "✅ {}개 도형 추가 완료!",
    "msg_link_added": "✅ 링크 추가 완료!\n페이지 {}",
    "msg_attachments_listed": "✅ 첨부 파일 목록!\n{}개 발견",
    "msg_redact_done": "✅ {}개 영역 교정 완료!",
    "msg_markdown_extracted": "✅ Markdown 추출 완료!\n{}페이지",
    "msg_pages_copied": "✅ {}페이지 복사 완료!",
    "msg_background_added": "✅ 배경색 추가 완료!\n{}페이지",
    "msg_markup_label_underline": "밑줄",
    "msg_markup_label_strikeout": "취소선",
    "msg_markup_label_squiggly": "물결선",
    "msg_text_markup_added": "✅ {} 추가 완료!\n'{}': {}개",
    "msg_textbox_inserted": "✅ 텍스트 상자 삽입 완료!\n페이지 {}",
    "msg_sticky_note_added": "✅ 스티키 노트 추가 완료!\n페이지 {}, 아이콘: {}",
    "msg_ink_annotation_added": "✅ 프리핸드 드로잉 추가 완료!\n페이지 {}, {}개 포인트",
    "msg_stroke_required": "드로잉 데이터가 없습니다.",
    "msg_invalid_stroke_format": "획 좌표 형식이 올바르지 않습니다.",
    "msg_freehand_signature_added": "✅ 프리핸드 서명 추가 완료!\n페이지 {}, {}개 획",
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
