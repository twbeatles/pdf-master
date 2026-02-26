import os
import logging

logger = logging.getLogger(__name__)


class WorkerAiOpsMixin:

    def ai_summarize(self):
        """AI 기반 PDF 요약"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        api_key = self.kwargs.get('api_key', '')
        language = self.kwargs.get('language', 'ko')
        style = self.kwargs.get('style', 'concise')
        max_pages = self.kwargs.get('max_pages', None)

        try:
            from ..ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_not_found"))
            return
        if self._is_pdf_encrypted(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_encrypted", os.path.basename(file_path)))
            return

        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return

        try:
            self._emit_progress_if_due(10)

            # AI 서비스 초기화
            ai_service = AIService(api_key=api_key)

            if not ai_service.is_available:
                self.error_signal.emit(self._get_msg("err_ai_unavailable"))
                return

            self._emit_progress_if_due(30)

            # PDF 요약 실행
            summary = ai_service.summarize_pdf(
                pdf_path=file_path,
                language=language,
                style=style,
                max_pages=max_pages
            )

            self._emit_progress_if_due(80)

            # 결과 저장
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# PDF 요약\n\n")
                    f.write(f"**원본 파일**: {os.path.basename(file_path)}\n\n")
                    f.write(f"---\n\n")
                    f.write(summary)

            # 결과를 kwargs에 저장 (UI에서 접근 가능)
            self.kwargs['summary_result'] = summary

            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ AI 요약 완료!\n{len(summary)} 글자")

        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            self.error_signal.emit(f"AI 요약 실패: {str(e)}")

    def ai_ask_question(self):
        """AI 기반 PDF 질의응답 (채팅)"""
        file_path = self.kwargs.get('file_path')
        question = self.kwargs.get('question', '')
        api_key = self.kwargs.get('api_key', '')
        conversation_history = self.kwargs.get('conversation_history')

        try:
            from ..ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_not_found"))
            return
        if self._is_pdf_encrypted(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_encrypted", os.path.basename(file_path)))
            return

        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return

        if not question.strip():
            self.error_signal.emit(self._get_msg("err_question_required"))
            return

        try:
            self._emit_progress_if_due(20)

            ai_service = AIService(api_key=api_key)

            if not ai_service.is_available:
                self.error_signal.emit("AI 서비스를 사용할 수 없습니다.")
                return

            self._emit_progress_if_due(40)

            # PDF 질의응답 실행
            answer = ai_service.ask_about_pdf(
                pdf_path=file_path,
                question=question,
                conversation_history=conversation_history
            )

            # 결과를 kwargs에 저장
            self.kwargs['answer_result'] = answer

            self._emit_progress_if_due(100)
            self.finished_signal.emit(f"✅ 답변 생성 완료!")

        except Exception as e:
            logger.error(f"AI Q&A failed: {e}")
            self.error_signal.emit(f"답변 생성 실패: {str(e)}")

    def ai_extract_keywords(self):
        """AI 기반 키워드 추출"""
        file_path = self.kwargs.get('file_path')
        api_key = self.kwargs.get('api_key', '')
        max_keywords = self.kwargs.get('max_keywords', 10)
        language = self.kwargs.get('language', 'ko')

        try:
            from ..ai_service import AIService
        except ImportError:
            self.error_signal.emit(self._get_msg("err_ai_module_not_found"))
            return

        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_not_found"))
            return
        if self._is_pdf_encrypted(file_path):
            self.error_signal.emit(self._get_msg("err_pdf_encrypted", os.path.basename(file_path)))
            return

        if not api_key:
            self.error_signal.emit(self._get_msg("err_api_key_required"))
            return

        try:
            self._emit_progress_if_due(20)

            ai_service = AIService(api_key=api_key)

            if not ai_service.is_available:
                self.error_signal.emit("AI 서비스를 사용할 수 없습니다.")
                return

            self._emit_progress_if_due(40)

            # 키워드 추출 실행
            keywords = ai_service.extract_keywords(
                pdf_path=file_path,
                max_keywords=max_keywords,
                language=language
            )

            # 결과를 kwargs에 저장
            self.kwargs['keywords_result'] = keywords

            self._emit_progress_if_due(100)

            if keywords:
                self.finished_signal.emit(f"✅ 키워드 추출 완료!\n{len(keywords)}개 키워드")
            else:
                self.finished_signal.emit("키워드를 추출할 수 없습니다.")

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            self.error_signal.emit(f"키워드 추출 실패: {str(e)}")

