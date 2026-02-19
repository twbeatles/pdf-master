import locale
import logging
import os
from .settings import load_settings

logger = logging.getLogger(__name__)

# Translation Dictionary
TRANSLATIONS = {
    "ko": {
        # General
        "app_title": "PDF Master",
        "ready": "✨ 준비 완료",
        "processing": "⏳ 작업 처리 중...",
        "cancelled": "🚫 작업이 취소되었습니다",
        "completed": "✅ 작업 완료!",
        "error": "❌ 오류 발생",
        "confirm": "확인",
        "cancel": "취소",
        "warning": "경고",
        "info": "정보",
        "file": "파일",
        "folder": "폴더",
        "open": "열기",
        "close": "닫기",
        "exit": "종료",
        "help": "도움말",
        "about": "정보",
        "shortcuts": "단축키 안내",
        "recent_files": "최근 파일",
        "recent_files": "최근 파일",
        "no_recent_files": "(최근 파일 없음)",
        "save": "저장",
        "theme_dark": "DARK",
        "theme_light": "LIGHT",
        "restart_required": "재시작 필요",
        "restart_required_msg": "언어 변경을 적용하려면 프로그램을 재시작해야 합니다.",
        
        # Menu
        "menu_file": "📁 파일",
        "menu_open": "📂 열기 (Ctrl+O)",
        "menu_exit": "🚪 종료 (Ctrl+Q)",
        "menu_recent": "📋 최근 파일",
        "menu_language": "🌐 언어 (Language)",
        "menu_help": "❓ 도움말",
        "menu_shortcuts": "⌨️ 단축키 안내",
        "menu_about": "ℹ️ 정보",
        "lang_auto": "자동 (시스템 설정)",
        "lang_ko": "한국어",
        "lang_en": "English",
        
        # Tabs
        "tab_merge": "병합",
        "tab_convert": "변환",
        "tab_page": "페이지",
        "tab_reorder": "순서 변경",
        "tab_edit": "편집/보안",
        "tab_batch": "일괄 처리",
        "tab_advanced": "고급",
        "tab_ai": "AI 요약",
        "subtab_edit": "편집",
        "subtab_extract": "추출",
        "subtab_markup": "마크업",
        "subtab_misc": "기타",

        # Preview Panel
        "preview_title": "📋 미리보기",
        "preview_default": "PDF 파일을 선택하면\n여기에 정보가 표시됩니다",
        "preview_encrypted": "🔒 암호화된 PDF\n비밀번호가 필요합니다",
        "preview_password_wrong": "❌ 비밀번호가 틀렸습니다",
        "password_title": "🔒 암호 입력",
        "password_msg": "'{}'\n\n비밀번호를 입력하세요:",
        "prev_page": "◀ 이전",
        "next_page": "다음 ▶",
        
        # Security
        "err_wrong_password": "❌ 비밀번호가 틀렸습니다.",
        "msg_decryption_success": "✅ PDF 복호화 완료!",
        "err_password_required": "비밀번호를 입력해주세요.",
        "err_pdf_not_encrypted": "PDF 파일이 암호화되어 있지 않습니다.",
        
        # Worker Actions
        "action_merge": "PDF 파일 병합",
        "action_convert_to_img": "PDF → 이미지 변환",
        "action_images_to_pdf": "이미지 → PDF 변환",
        "action_extract_text": "텍스트 추출",
        "action_split": "페이지 추출",
        "action_delete_pages": "페이지 삭제",
        "action_rotate": "페이지 회전",
        "action_add_page_numbers": "페이지 번호 추가",
        "action_watermark": "워터마크 적용",
        "action_encrypt": "PDF 암호화",
        "action_compress": "PDF 압축",
        "action_ai_summary": "AI PDF 분석",
        
        # Widgets
        "drop_title": "PDF 파일을 여기에 드래그하세요",
        "drop_hint": "또는 아래 버튼으로 선택",
        "drop_success": "✅ 여기에 놓으세요!",
        "btn_browse": "📂 파일 선택",
        "btn_clear": "🗑️ 지우기",
        "empty_title": "파일이 없습니다",
        "empty_desc": "파일을 드래그하거나 추가하세요",
        
        # About
        "about_desc": "모든 PDF 작업을 한 곳에서 처리하는 올인원 PDF 도구입니다.\n강력한 기능과 직관적인 UI를 제공합니다.",
        "tech_stack": "🛠️ 기술 스택:",
        
        # Shortcuts
        "shortcut_open": "🔹 Ctrl + O  :  파일 열기",
        "shortcut_exit": "🔹 Ctrl + Q  :  프로그램 종료",
        "shortcut_theme": "🔹 Ctrl + T  :  테마 전환",
        "shortcut_tabs": "🔹 Ctrl + 1~8 :  탭 전환",
        "shortcut_help": "🔹 F1  :  도움말 표시",
        
        # Worker Messages
        "msg_worker_busy": "이전 작업이 아직 진행 중입니다.\n완료될 때까지 기다리시겠습니까?",
        "msg_worker_cancelled": "작업이 취소되었습니다",
        "msg_worker_error": "작업 중 문제가 발생했습니다.\n{}",
        
        # Convert Tab
        "btn_convert_to_pdf": "📄 PDF로 변환",
        "grp_extract_text": "📝 텍스트 추출 (다중 파일)",
        "lbl_extract_drag": "PDF 파일들을 드래그하거나 추가하세요",
        "btn_add_pdf": "➕ PDF 추가",
        "btn_clear_all": "🗑️ 전체 삭제",
        "tooltip_clear_list": "목록 비우기",
        "btn_save_text": "📝 텍스트(.txt) 저장",
        
        # Page Tab
        "grp_page_number": "🔢 페이지 번호 삽입",
        "guide_page_format": "📌 형식: {n}=현재페이지, {total}=전체페이지",
        "lbl_position": "위치:",
        "lbl_format": "형식:",
        "btn_insert_page_number": "🔢 페이지 번호 삽입",
        "grp_split_page": "✂️ 페이지 추출",
        "lbl_split_range": "추출할 페이지 (예: 1-3, 5):",
        "btn_split_run": "✂️ 추출 실행",
        "grp_delete_page": "🗑️ 페이지 삭제",
        "lbl_delete_range": "삭제할 페이지 (예: 1, 3-5):",
        "btn_delete_run": "🗑️ 삭제 실행",
        "grp_rotate_page": "🔄 페이지 회전",
        "lbl_rotate_angle": "회전 각도:",
        "combo_rotate_90": "90° 시계방향",
        "combo_rotate_180": "180°",
        "combo_rotate_270": "270° 시계방향",
        "btn_rotate_run": "🔄 회전 실행",
        
        # Reorder Tab
        "guide_reorder": "🔀 PDF 페이지 순서를 변경합니다",
        "step_reorder_1": "1️⃣ PDF 파일 선택",
        "step_reorder_2": "2️⃣ 페이지를 드래그하여 순서 변경",
        "tooltip_reorder_list": "페이지를 드래그하여 순서를 변경하세요",
        "btn_reverse_order": "🔃 역순 정렬",
        "btn_save_order": "💾 순서 변경 저장",
        "msg_page_num": "📄 페이지 {}",

        
        # AI Summary Tab
        "grp_ai_summary": "🤖 AI 기반 PDF 요약",
        "msg_ai_unavailable": "❌ AI 기능을 사용할 수 없습니다\n\ngoogle-genai 패키지가 설치되지 않았습니다.\n인터넷 연결 후 설치해주세요:\npip install google-genai",
        "lbl_api_key": "Gemini API 키:",
        "ph_api_key": "API 키를 입력하세요...",
        "btn_save_key": "💾 저장",
        "msg_api_hint": "💡 <a href='https://aistudio.google.com/'>Google AI Studio</a>에서 무료 API 키를 발급받을 수 있습니다.",
        "step_ai_1": "1️⃣ PDF 파일 선택",
        "lbl_ai_file": "요약할 PDF 파일",
        "step_ai_2": "2️⃣ 요약 옵션",
        "lbl_ai_style": "스타일:",
        "style_concise": "간결하게",
        "style_detailed": "상세하게",
        "style_bullet": "불릿 포인트",
        "lbl_ai_lang": "언어:",
        "lbl_max_pages": "최대 페이지:",
        "tooltip_max_pages": "0 = 전체 페이지",
        "btn_ai_run": "🤖 AI 요약 실행",
        "tooltip_ai_unavailable": "google-genai 패키지가 설치되지 않음",
        "step_ai_3": "3️⃣ 요약 결과",
        "ph_ai_result": "요약 결과가 여기에 표시됩니다...",
        "msg_ai_disabled": "AI 기능을 사용할 수 없습니다",
        "btn_save_summary": "📄 요약 저장 (.txt)",
        "msg_key_saved": "API 키가 저장되었습니다",
        "msg_no_summary": "저장할 요약 결과가 없습니다.",
        "dlg_save_summary": "요약 저장",
        "msg_summary_saved": "요약이 저장되었습니다",
        "msg_enter_key": "Gemini API 키를 입력하세요.",
        "msg_select_pdf": "PDF 파일을 선택하세요.",
        "msg_ai_working": "⏳ AI가 요약 중입니다...",
        
        # Thumbnail Grid
        "grp_thumb": "🖼️ 페이지 썸네일 그리드",
        "desc_thumb": "PDF의 모든 페이지를 그리드로 미리볼 수 있습니다",
        "lbl_thumb_file": "PDF 파일",
        "btn_show_grid": "🔲 썸네일 그리드 보기",
        "title_thumb_grid": "📋 페이지 썸네일 - {}",
        "status_page_sel": "📄 {}페이지 선택됨",
        
        # Merge Tab
        "grp_metadata": "📋 메타데이터 수정",
        "lbl_title": "제목:",
        "lbl_author": "작성자:",
        "lbl_subject": "주제:",
        "btn_save_metadata": "💾 메타데이터 저장",
        "grp_watermark": "💧 워터마크 삽입",
        "ph_watermark_text": "워터마크 텍스트",
        "color_gray": "회색",
        "color_black": "검정",
        "color_red": "빨강",
        "color_blue": "파랑",
        "btn_apply_watermark": "💧 워터마크 적용",
        "grp_security": "🔒 보안 & 압축",
        "ph_password": "비밀번호 입력",
        "btn_encrypt": "🔒 암호화",
        "btn_compress": "📦 압축",
        
        
        # Merge Tab
        "guide_merge": "📎 여러 PDF 파일을 하나로 합칩니다",
        "step_merge_1": "1️⃣ PDF 파일들을 아래에 드래그하세요 (순서 조정 가능)",
        "lbl_merge_count": "📁 {}개 파일",
        "btn_remove_sel": "➖ 선택 삭제",
        "btn_clear_merge": "🧹 전체 삭제",
        "step_merge_2": "2️⃣ 병합 실행",
        "btn_run_merge": "🚀 PDF 병합 실행",
        "msg_merge_count_error": "2개 이상의 PDF 파일이 필요합니다.",
        "msg_confirm_clear": "{}개 파일을 모두 삭제하시겠습니까?",
        "dlg_title_pdf": "PDF 선택",
        
        # Convert Tab (Additional)
        "grp_pdf_to_img": "🖼️ PDF → 이미지 변환 (다중 파일)",
        "step_pdf_to_img": "1️⃣ PDF 파일들을 드래그하거나 추가하세요",
        "lbl_format": "포맷:",
        "lbl_dpi": "해상도(DPI):",
        "btn_convert_to_img": "🖼️ 이미지로 변환",
        "grp_img_to_pdf": "📄 이미지 → PDF 변환",
        "step_img_to_pdf": "1️⃣ 이미지 파일들을 아래에 드래그하세요",
        "btn_add_img": "➕ 이미지 추가",
        "btn_clear_img": "🧹 초기화",
        "dlg_title_img": "이미지 선택",
        
        # Batch Tab
        "guide_batch": "📦 여러 PDF에 동일한 작업을 일괄 적용합니다",
        "step_batch_1": "1️⃣ PDF 파일들 선택",
        "btn_add_files": "➕ 파일 추가",
        "btn_add_folder": "📁 폴더 전체",
        "btn_clear_list": "🧹 초기화",
        "step_batch_2": "2️⃣ 적용할 작업 선택",
        "lbl_operation": "작업:",
        "op_compress": "📦 압축",
        "op_watermark": "💧 워터마크",
        "op_encrypt": "🔒 암호화",
        "op_rotate": "🔄 회전(90°)",
        "lbl_batch_option": "텍스트/암호:",
        "ph_batch_option": "워터마크 텍스트 또는 비밀번호",
        "step_batch_3": "3️⃣ 출력 폴더 선택 및 실행",
        "btn_run_batch": "🚀 일괄 처리 실행",

        # Advanced Tab - Edit Subtab
        "grp_split_pdf": "✂️ PDF 분할",
        "lbl_split_mode": "분할 모드:",
        "mode_split_page": "각 페이지별",
        "mode_split_range": "범위 지정",
        "ph_split_range": "예: 1-3, 5-7, 10-12",
        "btn_split_pdf": "✂️ PDF 분할 실행",
        "grp_stamp": "📌 스탬프 추가",
        "lbl_stamp_text": "스탬프:",
        "stamp_confidential": "기밀",
        "stamp_approved": "승인됨",
        "stamp_draft": "초안",
        "stamp_final": "최종본",
        "stamp_no_copy": "복사본 금지",
        "lbl_stamp_pos": "위치:",
        "pos_top_right": "우상단",
        "pos_top_left": "좌상단",
        "pos_bottom_right": "우하단",
        "pos_bottom_left": "좌하단",
        "btn_add_stamp": "📌 스탬프 추가",
        "grp_crop": "📐 여백 자르기 (Crop)",
        "lbl_left": "좌:", 
        "lbl_top": "상:", 
        "lbl_right": "우:", 
        "lbl_bottom": "하:",
        "tooltip_crop": "측 자르기 (pt)",
        "btn_crop": "📐 여백 자르기",
        "grp_blank_page": "📄 빈 페이지 삽입",
        "lbl_blank_pos": "삽입 위치 (페이지):",
        "btn_insert_blank": "📄 빈 페이지 삽입",
        "grp_resize_page": "📐 페이지 크기 변경",
        "lbl_size": "크기:",
        "btn_resize": "📐 크기 변경",
        "grp_duplicate": "📋 페이지 복제",
        "lbl_dup_count": "복제 횟수:",
        "btn_duplicate": "📋 페이지 복제",
        "grp_reverse_page": "🔄 페이지 역순 정렬",
        "btn_reverse_page": "🔄 역순 정렬",
        
        # Advanced Tab - Extract Subtab
        "grp_extract_link": "🔗 PDF 링크 추출",
        "btn_extract_link": "🔗 링크 추출",
        "grp_extract_img": "🖼️ 이미지 추출",
        "btn_extract_img_adv": "🖼️ 이미지 추출",
        "grp_extract_table": "📊 테이블 추출",
        "btn_extract_table": "📊 테이블 추출 (CSV)",
        "grp_extract_bookmark": "📑 북마크/목차 추출",
        "btn_extract_bookmark": "📑 북마크 추출",
        "grp_pdf_info": "📊 PDF 정보/통계",
        "btn_extract_info": "📊 정보 추출",
        "grp_extract_md": "📝 Markdown 추출",
        "btn_extract_md": "📝 Markdown으로 추출",

        # Advanced Tab - Markup Subtab
        "grp_search_hi": "🔍 텍스트 검색 & 하이라이트",
        "lbl_keyword": "검색어:",
        "ph_search": "검색할 텍스트 입력...",
        "btn_search_text": "🔍 검색",
        "tooltip_search_text": "텍스트 위치 검색",
        "btn_highlight": "🖍️ 하이라이트",
        "tooltip_highlight": "검색어에 노란색 하이라이트 표시",
        "grp_annot": "📝 주석 관리",
        "btn_list_annot": "📋 주석 목록",
        "tooltip_list_annot": "PDF에 있는 모든 주석 목록 추출",
        "btn_remove_annot": "🗑️ 주석 삭제",
        "tooltip_remove_annot": "PDF에서 모든 주석 제거",
        "grp_markup": "✒️ 텍스트 마크업",
        "ph_markup": "마크업할 텍스트...",
        "lbl_markup_type": "유형:",
        "type_underline": "밑줄",
        "type_strikeout": "취소선",
        "type_squiggly": "물결선",
        "btn_add_markup": "✒️ 마크업 추가",
        "grp_bg_color": "🎨 배경색 추가",
        "lbl_color": "색상:",
        "color_cream": "크림색",
        "color_light_yellow": "연노랑",
        "color_light_blue": "연파랑",
        "color_light_gray": "연회색",
        "color_white": "흰색",
        "btn_add_bg": "🎨 배경색 추가",
        "grp_redact": "🖤 텍스트 교정 (영구 삭제)",
        "lbl_redact_text": "삭제할 텍스트:",
        "ph_redact": "영구 삭제할 텍스트 입력...",
        "btn_redact": "🖤 텍스트 교정",
        "tooltip_redact": "⚠️ 텍스트를 영구적으로 삭제합니다",
        "grp_sticky": "📌 스티키 노트 (메모 주석)",
        "lbl_pos_x": "위치 X:",
        "lbl_pos_y": "Y:",
        "lbl_icon": "아이콘:",
        "lbl_content": "메모 내용:",
        "ph_sticky": "스티키 노트에 표시할 메모 내용...",
        "btn_add_sticky": "📌 스티키 노트 추가",
        "grp_ink": "✏️ 프리핸드 드로잉",
        "lbl_line_width": "선 두께:",
        "color_blue_ink": "파랑",
        "color_red_ink": "빨강",
        "color_black_ink": "검정",
        "color_green_ink": "녹색",
        "lbl_ink_guide": "📝 좌표 형식: x1,y1;x2,y2;x3,y3 (예: 100,100;150,120;200,100)",
        "ph_ink": "좌표 입력: 100,100;150,120;200,100",
        "btn_add_ink": "✏️ 프리핸드 드로잉 추가",

        # Advanced Tab - Misc Subtab
        "grp_form": "📝 PDF 양식 작성",
        "tooltip_form_list": "양식 필드 목록 (수정하려면 더블클릭)",
        "btn_detect_fields": "🔍 필드 감지",
        "btn_save_form": "💾 양식 저장",
        "grp_compare": "🔍 PDF 비교",
        "lbl_file_1": "📄 파일 1:",
        "lbl_file_2": "📄 파일 2:",
        "btn_compare_pdf": "🔍 PDF 비교",
        "tooltip_compare": "두 PDF의 텍스트 차이 분석",
        "grp_sig": "✍️ 전자 서명 삽입",
        "lbl_target_pdf": "PDF 파일:",
        "lbl_sig_img": "서명 이미지 (PNG/JPG):",
        "tooltip_sig_pos": "-1 = 마지막 페이지",
        "btn_insert_sig": "✍️ 서명 삽입",
        "grp_decrypt": "🔓 PDF 복호화",
        "lbl_pw": "비밀번호:",
        "ph_decrypt_pw": "암호화된 PDF의 비밀번호",
        "btn_decrypt": "🔓 복호화",
        "tooltip_decrypt": "암호 해제된 PDF로 저장",
        "grp_attach": "📎 첨부 파일 관리",
        "btn_list_attach": "📋 첨부 목록",
        "btn_add_attach": "➕ 파일 첨부",
        "btn_extract_attach": "📤 첨부 추출",
        
        # Common Action Status
        "undo_action": "↩️ 취소: {}",
        "redo_action": "↪️ 다시 실행: {}",
        "undo_empty": "취소할 작업이 없습니다",
        "redo_empty": "다시 실행할 작업이 없습니다",
        
        # Help Dialog
        "help_title": "도움말",
        "help_intro": "🔹 파일을 드래그하거나 버튼으로 선택하세요\n🔹 각 탭에서 원하는 작업을 선택하세요\n🔹 작업 완료 시 저장 위치를 지정합니다",
        "help_features": "주요 기능:\n• 📎 병합: 여러 PDF를 하나로\n• 🖼️ 변환: PDF ↔ 이미지\n• ✂️ 페이지: 추출, 삭제, 회전\n• 🔒 보안: 암호화, 워터마크",
        "btn_add_files_merge": "➕ 파일 추가",
        
        # Undo/Restore Messages (v4.4)
        "undo_failed_title": "실행 취소 실패",
        "undo_backup_not_found": "백업 파일을 찾을 수 없습니다.",
        "restore_success": "파일이 복원되었습니다",
        "restore_failed_title": "복원 실패",
        "restore_failed_msg": "파일 복원 중 오류: {}",
        "print_title": "인쇄",
        "print_no_file": "인쇄할 파일이 없습니다.",
        "print_sent": "인쇄 명령이 전송되었습니다",
        "print_error_title": "인쇄 오류",
        "print_error_msg": "인쇄 중 오류: {}",
        
        # Status Messages (v4.4)
        "msg_worker_cancelled": "작업이 취소되었습니다",
        "cancelling": "🚫 작업 취소 중...",
        "processing_status": "⏳ 작업 처리 중...",

        # v4.5 New Features
        # Draw Shapes
        "grp_draw_shapes": "📐 도형 그리기",
        "lbl_shape_type": "도형:",
        "shape_rect": "사각형",
        "shape_circle": "원",
        "shape_line": "선",
        "lbl_shape_x": "X:",
        "lbl_shape_y": "Y:",
        "lbl_shape_width": "너비:",
        "lbl_shape_height": "높이:",
        "lbl_line_color": "선 색상:",
        "lbl_fill_color": "채우기:",
        "btn_draw_shape": "📐 도형 그리기",
        
        # Hyperlink
        "grp_add_link": "🔗 하이퍼링크 추가",
        "lbl_link_type": "링크 유형:",
        "link_url": "URL 링크",
        "link_page": "페이지 이동",
        "lbl_link_url": "URL:",
        "ph_link_url": "https://example.com",
        "lbl_target_page": "대상 페이지:",
        "lbl_link_area": "링크 영역 (x1,y1,x2,y2):",
        "ph_link_area": "100,700,300,750",
        "btn_add_link": "🔗 링크 추가",
        
        # Textbox
        "grp_insert_textbox": "📝 텍스트 상자 삽입",
        "lbl_textbox_content": "텍스트:",
        "ph_textbox_content": "삽입할 텍스트...",
        "lbl_textbox_x": "위치 X:",
        "lbl_textbox_y": "위치 Y:",
        "lbl_textbox_fontsize": "폰트 크기:",
        "lbl_textbox_color": "텍스트 색상:",
        "btn_insert_textbox": "📝 텍스트 삽입",
        
        # Copy Page Between Docs
        "grp_copy_page": "📋 다른 PDF에서 페이지 복사",
        "lbl_source_pdf": "소스 PDF:",
        "lbl_copy_pages": "복사할 페이지:",
        "ph_copy_pages": "예: 1-3, 5",
        "lbl_insert_pos": "삽입 위치:",
        "tooltip_insert_pos": "0 = 맨 앞, -1 = 맨 뒤",
        "btn_copy_pages": "📋 페이지 복사",
        
        # Image Watermark Enhanced
        "grp_img_watermark": "🖼️ 이미지 워터마크",
        "lbl_wm_image": "이미지 파일:",
        "lbl_wm_position": "위치:",
        "pos_center": "중앙",
        "pos_top_center": "상단 중앙",
        "pos_bottom_center": "하단 중앙",
        "lbl_wm_scale": "크기 (%):",
        "lbl_wm_opacity": "투명도:",
        "btn_apply_img_watermark": "🖼️ 이미지 워터마크 적용",
        
        # Preview Print
        "btn_print_preview": "🖨️ 인쇄",
        "tooltip_print_preview": "현재 PDF 인쇄",
        
        # Folder Drop
        "msg_folder_dropped": "폴더에서 {}개의 PDF 파일을 추가했습니다",
        "msg_folder_no_pdf": "폴더에 PDF 파일이 없습니다",
        
        # AI Chat
        "grp_ai_chat": "💬 PDF 채팅",
        "step_ai_chat": "📄 PDF에 대해 질문하세요",
        "ph_ai_question": "질문을 입력하세요...",
        "btn_ask_ai": "💬 질문하기",
        "lbl_chat_history": "대화 기록:",
        "msg_ai_thinking": "🤔 AI가 답변을 생성 중...",
        "msg_chat_cleared": "대화 기록이 삭제되었습니다",
        "btn_clear_chat": "🧹 대화 삭제",
        
        # Keyword Extraction
        "grp_keywords": "🏷️ 키워드 추출",
        "lbl_max_keywords": "최대 키워드 수:",
        "btn_extract_keywords": "🏷️ 키워드 추출",
        "lbl_keywords_result": "추출된 키워드:",
        "msg_no_keywords": "키워드를 추출할 수 없습니다",
        
        # Background Color Enhanced
        "lbl_custom_color": "사용자 지정:",
        "btn_pick_color": "🎨 색상 선택",
        "lbl_bg_pages": "적용 페이지:",
        "ph_bg_pages": "전체 또는 1-3, 5",

        # v4.5 Worker Error Messages (i18n)
        "err_ai_module_not_found": "AI 서비스 모듈을 찾을 수 없습니다.",
        "err_pdf_not_found": "PDF 파일을 찾을 수 없습니다.",
        "err_api_key_required": "Gemini API 키가 필요합니다.\n설정에서 API 키를 입력해주세요.",
        "err_ai_unavailable": "AI 서비스를 사용할 수 없습니다.\ngoogle-generativeai 패키지를 설치해주세요.",
        "err_question_required": "질문을 입력해주세요.",
        "err_input_file_missing": "입력 파일이 존재하지 않습니다.",
        "err_output_path_missing": "출력 경로가 지정되지 않았습니다.",
        "err_no_files_selected": "병합할 파일이 선택되지 않았습니다.",
        "err_no_valid_pdf": "유효한 PDF 파일이 없습니다.",
        "err_pdf_encrypted": "파일이 암호화되어 있습니다: {}",
        "err_file_access_denied": "파일 접근 권한이 없습니다: {}",
        "err_pdf_corrupted": "PDF 파일이 손상되었거나 형식이 올바르지 않습니다.",
        "err_operation_failed": "오류 발생: {}",
        "err_cancelled": "작업이 취소되었습니다.",
        
        # v4.5: Worker management
        "task_in_progress": "작업 진행 중",
        "task_wait_or_cancel": "이전 작업이 아직 진행 중입니다.\n완료될 때까지 기다리시겠습니까?",
        
        # v4.5: File validation
        "err_file_too_large": "파일이 너무 큽니다: {} (최대 {})",
        "err_file_too_small": "파일이 너무 작거나 손상되었습니다.",
        "password_retry": "비밀번호가 틀렸습니다. 다시 시도하시겠습니까?",
        "batch_processing_file": "처리 중: {}",

    },
    "en": {
        # General
        "app_title": "PDF Master",
        "ready": "✨ Ready",
        "processing": "⏳ Processing...",
        "cancelled": "🚫 Operation cancelled",
        "completed": "✅ Completed!",
        "error": "❌ Error",
        "confirm": "OK",
        "cancel": "Cancel",
        "warning": "Warning",
        "info": "Info",
        "file": "File",
        "folder": "Folder",
        "open": "Open",
        "close": "Close",
        "exit": "Exit",
        "help": "Help",
        "about": "About",
        "shortcuts": "Shortcuts",
        "recent_files": "Recent Files",
        "recent_files": "Recent Files",
        "no_recent_files": "(No recent files)",
        "save": "Save",
        "theme_dark": "DARK",
        "theme_light": "LIGHT",
        "restart_required": "Restart Required",
        "restart_required_msg": "You must restart the application to apply language changes.",

        # Menu
        "menu_file": "📁 File",
        "menu_open": "📂 Open (Ctrl+O)",
        "menu_exit": "🚪 Exit (Ctrl+Q)",
        "menu_recent": "📋 Recent Files",
        "menu_language": "🌐 Language",
        "menu_help": "❓ Help",
        "menu_shortcuts": "⌨️ Shortcuts",
        "menu_about": "ℹ️ About",
        "lang_auto": "Auto (System Default)",
        "lang_ko": "Korean",
        "lang_en": "English",

        # Tabs
        "tab_merge": "Merge",
        "tab_convert": "Convert",
        "tab_page": "Page",
        "tab_reorder": "Reorder",
        "tab_edit": "Edit/Sec",
        "tab_batch": "Batch",
        "tab_advanced": "Advanced",
        "tab_ai": "AI Summary",
        "subtab_edit": "Edit",
        "subtab_extract": "Extract",
        "subtab_markup": "Markup",
        "subtab_misc": "Misc",

        # Preview Panel
        "preview_title": "📋 Preview",
        "preview_default": "Select a PDF file to\nview information here",
        "preview_encrypted": "🔒 Encrypted PDF\nPassword required",
        "preview_password_wrong": "❌ Incorrect password",
        "password_title": "🔒 Enter Password",
        "password_msg": "'{}'\n\nEnter password:",
        "prev_page": "◀ PREV",
        "next_page": "NEXT ▶",

        # Security
        "err_wrong_password": "❌ Incorrect password.",
        "msg_decryption_success": "✅ PDF decrypted successfully!",
        "err_password_required": "Password is required.",
        "err_pdf_not_encrypted": "PDF file is not encrypted.",

        # Worker Actions
        "action_merge": "Merge PDF",
        "action_convert_to_img": "PDF → Image",
        "action_images_to_pdf": "Image → PDF",
        "action_extract_text": "Extract Text",
        "action_split": "Extract Pages",
        "action_delete_pages": "Delete Pages",
        "action_rotate": "Rotate Pages",
        "action_add_page_numbers": "Add Page Numbers",
        "action_watermark": "Add Watermark",
        "action_encrypt": "Encrypt PDF",
        "action_compress": "Compress PDF",
        "action_ai_summary": "AI Analysis",

        # Widgets
        "drop_title": "Drag & Drop PDF here",
        "drop_hint": "or select using button below",
        "drop_success": "✅ Drop here!",
        "btn_browse": "📂 Select File",
        "btn_clear": "🗑️ Clear",
        "empty_title": "No File",
        "empty_desc": "Drag & drop or add a file",

        # About
        "about_desc": "All-in-one PDF tool for all your needs.\nPowerful features with intuitive UI.",
        "tech_stack": "🛠️ Tech Stack:",

        # Advanced Tab - Markup Subtab
        "grp_search_hi": "🔍 Search & Highlight",
        "lbl_keyword": "Keyword:",
        "ph_search": "Text to search...",
        "btn_search_text": "🔍 Search",
        "tooltip_search_text": "Search text location",
        "btn_highlight": "🖍️ Highlight",
        "tooltip_highlight": "Highlight keyword in yellow",
        "grp_annot": "📝 Annotation Manager",
        "btn_list_annot": "📋 List Annotations",
        "tooltip_list_annot": "Extract all annotations from PDF",
        "btn_remove_annot": "🗑️ Remove Annotations",
        "tooltip_remove_annot": "Remove all annotations from PDF",
        "grp_markup": "✒️ Text Markup",
        "ph_markup": "Text to markup...",
        "lbl_markup_type": "Type:",
        "type_underline": "Underline",
        "type_strikeout": "Strikeout",
        "type_squiggly": "Squiggly",
        "btn_add_markup": "✒️ Add Markup",
        "grp_bg_color": "🎨 Add Background Color",
        "lbl_color": "Color:",
        "color_cream": "Cream",
        "color_light_yellow": "Light Yellow",
        "color_light_blue": "Light Blue",
        "color_light_gray": "Light Gray",
        "color_white": "White",
        "btn_add_bg": "🎨 Add Background",
        "grp_redact": "🖤 Redact Text (Permanent)",
        "lbl_redact_text": "Text to Redact:",
        "ph_redact": "Text to permanently delete...",
        "btn_redact": "🖤 Redact Text",
        "tooltip_redact": "⚠️ Permanently deletes text",
        "grp_sticky": "📌 Sticky Note",
        "lbl_pos_x": "Pos X:",
        "lbl_pos_y": "Y:",
        "lbl_icon": "Icon:",
        "lbl_content": "Content:",
        "ph_sticky": "Sticky note content...",
        "btn_add_sticky": "📌 Add Sticky Note",
        "grp_ink": "✏️ Freehand Drawing",
        "lbl_line_width": "Width:",
        "color_blue_ink": "Blue",
        "color_red_ink": "Red",
        "color_black_ink": "Black",
        "color_green_ink": "Green",
        "lbl_ink_guide": "📝 Layout: x1,y1;x2,y2... (e.g. 100,100;150,120)",
        "ph_ink": "Coords: 100,100;150,120...",
        "btn_add_ink": "✏️ Add Drawing",

        # Advanced Tab - Misc Subtab
        "grp_form": "📝 PDF Form Filling",
        "tooltip_form_list": "Form fields (Double click to edit)",
        "btn_detect_fields": "🔍 Detect Fields",
        "btn_save_form": "💾 Save Form",
        "grp_compare": "🔍 Compare PDFs",
        "lbl_file_1": "📄 File 1:",
        "lbl_file_2": "📄 File 2:",
        "btn_compare_pdf": "🔍 Compare PDFs",
        "tooltip_compare": "Analyze text differences",
        "grp_sig": "✍️ Digital Signature",
        "lbl_target_pdf": "PDF File:",
        "lbl_sig_img": "Signature Img (PNG/JPG):",
        "tooltip_sig_pos": "-1 = Last Page",
        "btn_insert_sig": "✍️ Insert Signature",
        "grp_decrypt": "🔓 Decrypt PDF",
        "lbl_pw": "Password:",
        "ph_decrypt_pw": "Password for encrypted PDF",
        "btn_decrypt": "🔓 Decrypt",
        "tooltip_decrypt": "Save as decrypted PDF",
        "grp_attach": "📎 Attachments",
        "btn_list_attach": "📋 List Attachments",
        "btn_add_attach": "➕ Add Attachment",
        "btn_extract_attach": "📤 Extract Attachments",

        # Shortcuts
        "shortcut_open": "🔹 Ctrl + O  :  Open File",
        "shortcut_exit": "🔹 Ctrl + Q  :  Exit",
        "shortcut_theme": "🔹 Ctrl + T  :  Toggle Theme",
        "shortcut_tabs": "🔹 Ctrl + 1~8 :  Switch Tab",
        "shortcut_help": "🔹 F1  :  Help",

        # Worker Messages
        "msg_worker_busy": "Previous task is still running.\nWait for it to complete?",
        "msg_worker_cancelled": "Operation cancelled",
        "msg_worker_error": "Problem occurred during operation.\n{}",

        # Convert Tab
        "btn_convert_to_pdf": "📄 Convert to PDF",
        "grp_extract_text": "📝 Extract Text (Batch)",
        "lbl_extract_drag": "Drag & Drop PDF files here",
        "btn_add_pdf": "➕ Add PDF",
        "btn_clear_all": "🗑️ Clear All",
        "tooltip_clear_list": "Clear the list",
        "btn_save_text": "📝 Save Text (.txt)",
        
        # Page Tab
        "grp_page_number": "🔢 Insert Page Numbers",
        "guide_page_format": "📌 Format: {n}=current, {total}=total",
        "lbl_position": "Position:",
        "lbl_format": "Format:",
        "btn_insert_page_number": "🔢 Insert Page Numbers",
        "grp_split_page": "✂️ Extract Pages",
        "lbl_split_range": "Pages to extract (e.g., 1-3, 5):",
        "btn_split_run": "✂️ Extract Pages",
        "grp_delete_page": "🗑️ Delete Pages",
        "lbl_delete_range": "Pages to delete (e.g., 1, 3-5):",
        "btn_delete_run": "🗑️ Delete Pages",
        "grp_rotate_page": "🔄 Rotate Pages",
        "lbl_rotate_angle": "Angle:",
        "combo_rotate_90": "90° CW",
        "combo_rotate_180": "180°",
        "combo_rotate_270": "270° CW",
        "btn_rotate_run": "🔄 Rotate Pages",
        
        # Reorder Tab
        "guide_reorder": "🔀 Reorder PDF Pages",
        "step_reorder_1": "1️⃣ Select PDF File",
        "step_reorder_2": "2️⃣ Drag to Reorder Pages",
        "tooltip_reorder_list": "Drag pages to reorder",
        "btn_reverse_order": "🔃 Reverse Order",
        "btn_save_order": "💾 Save Order",
        "msg_page_num": "📄 Page {}",

        
        # AI Summary Tab
        "grp_ai_summary": "🤖 AI PDF Summary",
        "msg_ai_unavailable": "❌ AI features unavailable\n\ngoogle-genai package is missing.\nPlease install it:\npip install google-genai",
        "lbl_api_key": "Gemini API Key:",
        "ph_api_key": "Enter API Key...",
        "btn_save_key": "💾 Save",
        "msg_api_hint": "💡 Get free API key from <a href='https://aistudio.google.com/'>Google AI Studio</a>",
        "step_ai_1": "1️⃣ Select PDF File",
        "lbl_ai_file": "PDF to Summarize",
        "step_ai_2": "2️⃣ Options",
        "lbl_ai_style": "Style:",
        "style_concise": "Concise",
        "style_detailed": "Detailed",
        "style_bullet": "Bullet Points",
        "lbl_ai_lang": "Language:",
        "lbl_max_pages": "Max Pages:",
        "tooltip_max_pages": "0 = All Pages",
        "btn_ai_run": "🤖 Run AI Summary",
        "tooltip_ai_unavailable": "google-genai package not installed",
        "step_ai_3": "3️⃣ Result",
        "ph_ai_result": "Summary result will appear here...",
        "msg_ai_disabled": "AI features unavailable",
        "btn_save_summary": "📄 Save Summary (.txt)",
        "msg_key_saved": "API Key saved",
        "msg_no_summary": "No summary result to save.",
        "dlg_save_summary": "Save Summary",
        "msg_summary_saved": "Summary saved",
        "msg_enter_key": "Please enter Gemini API Key.",
        "msg_select_pdf": "Please select a PDF file.",
        "msg_ai_working": "⏳ AI is summarizing...",

        # Thumbnail Grid
        "grp_thumb": "🖼️ Page Thumbnail Grid",
        "desc_thumb": "View all PDF pages in a grid",
        "lbl_thumb_file": "PDF File",
        "btn_show_grid": "🔲 Show Thumbnail Grid",
        "title_thumb_grid": "📋 Page Thumbnails - {}",
        "status_page_sel": "📄 Page {} selected",

        # Edit/Security Tab
        "grp_metadata": "📋 Edit Metadata",
        "lbl_title": "Title:",
        "lbl_author": "Author:",
        "lbl_subject": "Subject:",
        "btn_save_metadata": "💾 Save Metadata",
        "grp_watermark": "💧 Add Watermark",
        "ph_watermark_text": "Watermark text",
        "color_gray": "Gray",
        "color_black": "Black",
        "color_red": "Red",
        "color_blue": "Blue",
        "btn_apply_watermark": "💧 Apply Watermark",
        "grp_security": "🔒 Security & Compress",
        "ph_password": "Enter password",
        "btn_encrypt": "🔒 Encrypt",
        "btn_compress": "📦 Compress",
        
        
        # Merge Tab
        "guide_merge": "📎 Merge multiple PDF files into one",
        "step_merge_1": "1️⃣ Drag & Drop PDF files below (Reorderable)",
        "lbl_merge_count": "📁 {} Files",
        "btn_remove_sel": "➖ Remove Selected",
        "btn_clear_merge": "🧹 Clear All",
        "step_merge_2": "2️⃣ Run Merge",
        "btn_run_merge": "🚀 Run PDF Merge",
        "msg_merge_count_error": "At least 2 PDF files are required.",
        "msg_confirm_clear": "Delete all {} files?",
        "dlg_title_pdf": "Select PDF",
        
        # Convert Tab (Additional)
        "grp_pdf_to_img": "🖼️ PDF → Image (Batch)",
        "step_pdf_to_img": "1️⃣ Drag & Drop PDF files here",
        "lbl_format": "Format:",
        "lbl_dpi": "Resolution (DPI):",
        "btn_convert_to_img": "🖼️ Convert to Image",
        "grp_img_to_pdf": "📄 Image → PDF",
        "step_img_to_pdf": "1️⃣ Drag & Drop image files below",
        "btn_add_img": "➕ Add Images",
        "btn_clear_img": "🧹 Clear",
        "dlg_title_img": "Select Images",
        
        # Batch Tab
        "guide_batch": "📦 Batch Processing",
        "step_batch_1": "1️⃣ Select PDF Files",
        "btn_add_files": "➕ Add Files",
        "btn_add_folder": "📁 Add Folder",
        "btn_clear_list": "🧹 Clear",
        "step_batch_2": "2️⃣ Select Operation",
        "lbl_operation": "Op:",
        "op_compress": "📦 Compress",
        "op_watermark": "💧 Watermark",
        "op_encrypt": "🔒 Encrypt",
        "op_rotate": "🔄 Rotate (90°)",
        "lbl_batch_option": "Text/Pw:",
        "ph_batch_option": "Watermark or Password",
        "step_batch_3": "3️⃣ Select Output & Run",
        "btn_run_batch": "🚀 Run Batch",

        # Advanced Tab - Edit Subtab
        "grp_split_pdf": "✂️ Split PDF",
        "lbl_split_mode": "Split Mode:",
        "mode_split_page": "By Page",
        "mode_split_range": "By Range",
        "ph_split_range": "e.g. 1-3, 5-7, 10-12",
        "btn_split_pdf": "✂️ Split PDF",
        "grp_stamp": "📌 Add Stamp",
        "lbl_stamp_text": "Stamp:",
        "stamp_confidential": "CONFIDENTIAL",
        "stamp_approved": "APPROVED",
        "stamp_draft": "DRAFT",
        "stamp_final": "FINAL",
        "stamp_no_copy": "DO NOT COPY",
        "lbl_stamp_pos": "Pos:",
        "pos_top_right": "Top-Right",
        "pos_top_left": "Top-Left",
        "pos_bottom_right": "Bot-Right",
        "pos_bottom_left": "Bot-Left",
        "btn_add_stamp": "📌 Add Stamp",
        "grp_crop": "📐 Crop Margins",
        "lbl_left": "L:", 
        "lbl_top": "T:", 
        "lbl_right": "R:", 
        "lbl_bottom": "B:",
        "tooltip_crop": "Crop margin (pt)",
        "btn_crop": "📐 Crop",
        "grp_blank_page": "📄 Insert Blank Page",
        "lbl_blank_pos": "Position (Page):",
        "btn_insert_blank": "📄 Insert Blank Page",
        "grp_resize_page": "📐 Resize Pages",
        "lbl_size": "Size:",
        "btn_resize": "📐 Resize",
        "grp_duplicate": "📋 Duplicate Page",
        "lbl_dup_count": "Count:",
        "btn_duplicate": "📋 Duplicate",
        "grp_reverse_page": "🔄 Reverse Pages",
        "btn_reverse_page": "🔄 Reverse",
        
        # Advanced Tab - Extract Subtab
        "grp_extract_link": "🔗 Extract Links",
        "btn_extract_link": "🔗 Extract Links",
        "grp_extract_img": "🖼️ Extract Images",
        "btn_extract_img_adv": "🖼️ Extract Images",
        "grp_extract_table": "📊 Extract Tables",
        "btn_extract_table": "📊 Extract Tables (CSV)",
        "grp_extract_bookmark": "📑 Extract Bookmarks",
        "btn_extract_bookmark": "📑 Extract Bookmarks",
        "grp_pdf_info": "📊 PDF Info",
        "btn_extract_info": "📊 Extract Info",
        "grp_extract_md": "📝 Extract Markdown",
        "btn_extract_md": "📝 Extract Markdown",

        # Common Action Status
        "undo_action": "↩️ Undo: {}",
        "redo_action": "↪️ Redo: {}",
        "undo_empty": "Nothing to undo",
        "redo_empty": "Nothing to redo",
        
        # Help Dialog
        "help_title": "Help",
        "help_intro": "🔹 Drag & drop or select files using buttons\n🔹 Choose your operation from tabs\n🔹 Specify output location when done",
        "help_features": "Key Features:\n• 📎 Merge: Combine PDFs\n• 🖼️ Convert: PDF ↔ Image\n• ✂️ Pages: Extract, delete, rotate\n• 🔒 Security: Encrypt, watermark",
        "btn_add_files_merge": "➕ Add Files",
        
        # Undo/Restore Messages (v4.4)
        "undo_failed_title": "Undo Failed",
        "undo_backup_not_found": "Backup file not found.",
        "restore_success": "File restored successfully",
        "restore_failed_title": "Restore Failed",
        "restore_failed_msg": "Error restoring file: {}",
        "print_title": "Print",
        "print_no_file": "No file to print.",
        "print_sent": "Print command sent",
        "print_error_title": "Print Error",
        "print_error_msg": "Error printing: {}",
        
        # Status Messages (v4.4)
        "msg_worker_cancelled": "Operation cancelled",
        "cancelling": "🚫 Cancelling...",
        "processing_status": "⏳ Processing...",

        # v4.5 New Features
        # Draw Shapes
        "grp_draw_shapes": "📐 Draw Shapes",
        "lbl_shape_type": "Shape:",
        "shape_rect": "Rectangle",
        "shape_circle": "Circle",
        "shape_line": "Line",
        "lbl_shape_x": "X:",
        "lbl_shape_y": "Y:",
        "lbl_shape_width": "Width:",
        "lbl_shape_height": "Height:",
        "lbl_line_color": "Line Color:",
        "lbl_fill_color": "Fill:",
        "btn_draw_shape": "📐 Draw Shape",
        
        # Hyperlink
        "grp_add_link": "🔗 Add Hyperlink",
        "lbl_link_type": "Link Type:",
        "link_url": "URL Link",
        "link_page": "Go to Page",
        "lbl_link_url": "URL:",
        "ph_link_url": "https://example.com",
        "lbl_target_page": "Target Page:",
        "lbl_link_area": "Link Area (x1,y1,x2,y2):",
        "ph_link_area": "100,700,300,750",
        "btn_add_link": "🔗 Add Link",
        
        # Textbox
        "grp_insert_textbox": "📝 Insert Textbox",
        "lbl_textbox_content": "Text:",
        "ph_textbox_content": "Text to insert...",
        "lbl_textbox_x": "Position X:",
        "lbl_textbox_y": "Position Y:",
        "lbl_textbox_fontsize": "Font Size:",
        "lbl_textbox_color": "Text Color:",
        "btn_insert_textbox": "📝 Insert Text",
        
        # Copy Page Between Docs
        "grp_copy_page": "📋 Copy Pages from Another PDF",
        "lbl_source_pdf": "Source PDF:",
        "lbl_copy_pages": "Pages to Copy:",
        "ph_copy_pages": "e.g., 1-3, 5",
        "lbl_insert_pos": "Insert Position:",
        "tooltip_insert_pos": "0 = Start, -1 = End",
        "btn_copy_pages": "📋 Copy Pages",
        
        # Image Watermark Enhanced
        "grp_img_watermark": "🖼️ Image Watermark",
        "lbl_wm_image": "Image File:",
        "lbl_wm_position": "Position:",
        "pos_center": "Center",
        "pos_top_center": "Top Center",
        "pos_bottom_center": "Bottom Center",
        "lbl_wm_scale": "Scale (%):",
        "lbl_wm_opacity": "Opacity:",
        "btn_apply_img_watermark": "🖼️ Apply Image Watermark",
        
        # Preview Print
        "btn_print_preview": "🖨️ Print",
        "tooltip_print_preview": "Print current PDF",
        
        # Folder Drop
        "msg_folder_dropped": "Added {} PDF files from folder",
        "msg_folder_no_pdf": "No PDF files in folder",
        
        # AI Chat
        "grp_ai_chat": "💬 PDF Chat",
        "step_ai_chat": "📄 Ask questions about the PDF",
        "ph_ai_question": "Enter your question...",
        "btn_ask_ai": "💬 Ask",
        "lbl_chat_history": "Chat History:",
        "msg_ai_thinking": "🤔 AI is generating response...",
        "msg_chat_cleared": "Chat history cleared",
        "btn_clear_chat": "🧹 Clear Chat",
        
        # Keyword Extraction
        "grp_keywords": "🏷️ Keyword Extraction",
        "lbl_max_keywords": "Max Keywords:",
        "btn_extract_keywords": "🏷️ Extract Keywords",
        "lbl_keywords_result": "Extracted Keywords:",
        "msg_no_keywords": "Could not extract keywords",
        
        # Background Color Enhanced
        "lbl_custom_color": "Custom:",
        "btn_pick_color": "🎨 Pick Color",
        "lbl_bg_pages": "Apply to Pages:",
        "ph_bg_pages": "All or 1-3, 5",

        # v4.5 Worker Error Messages (i18n)
        "err_ai_module_not_found": "AI service module not found.",
        "err_pdf_not_found": "PDF file not found.",
        "err_api_key_required": "Gemini API key is required.\nPlease enter the API key in settings.",
        "err_ai_unavailable": "AI service is unavailable.\nPlease install google-generativeai package.",
        "err_question_required": "Please enter a question.",
        "err_input_file_missing": "Input file does not exist.",
        "err_output_path_missing": "Output path is not specified.",
        "err_no_files_selected": "No files selected for merge.",
        "err_no_valid_pdf": "No valid PDF files found.",
        "err_pdf_encrypted": "File is encrypted: {}",
        "err_file_access_denied": "Permission denied: {}",
        "err_pdf_corrupted": "PDF file is corrupted or has invalid format.",
        "err_operation_failed": "Error: {}",
        "err_cancelled": "Operation cancelled.",
        
        # v4.5: Worker management
        "task_in_progress": "Task in Progress",
        "task_wait_or_cancel": "Previous task is still running.\nWait for it to complete?",
        
        # v4.5: File validation
        "err_file_too_large": "File is too large: {} (max {})",
        "err_file_too_small": "File is too small or corrupted.",
        "password_retry": "Incorrect password. Would you like to try again?",
        "batch_processing_file": "Processing: {}",
    }
}

class TranslationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.settings = load_settings()
        self.current_lang = self.settings.get("language", "auto")
        
        # Auto-detect logic
        if self.current_lang == "auto":
            sys_lang = self._detect_system_language()
            if sys_lang.startswith("ko"):
                self.active_lang_code = "ko"
            else:
                self.active_lang_code = "en"
        else:
            self.active_lang_code = self.current_lang
            
        logger.info(f"TranslationManager initialized. Lang: {self.current_lang}, Active: {self.active_lang_code}")
        self._initialized = True

    def _detect_system_language(self) -> str:
        """비권장 API(locale.getdefaultlocale) 없이 시스템 언어를 감지."""
        candidates = []
        try:
            lang, _ = locale.getlocale()
            if lang:
                candidates.append(lang)
        except Exception:
            logger.debug("locale.getlocale() failed", exc_info=True)

        for env_key in ("LC_ALL", "LC_MESSAGES", "LANG"):
            env_val = os.environ.get(env_key)
            if env_val:
                candidates.append(env_val)

        for cand in candidates:
            normalized = str(cand).strip().lower()
            if normalized.startswith("ko"):
                return "ko"
        return "en"
        
    def get(self, key: str, *args) -> str:
        """
        Get translated string
        
        Args:
            key: Translation key
            args: Format arguments
        """
        lang_dict = TRANSLATIONS.get(self.active_lang_code, TRANSLATIONS["en"])
        text = lang_dict.get(key, key) # Fallback to key if not found
        
        if args:
            try:
                return text.format(*args)
            except IndexError:
                return text
        return text

# Global instance
tm = TranslationManager()
