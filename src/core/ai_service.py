"""
AI Service for PDF Master v4.2
Gemini API를 활용한 PDF 요약 서비스를 제공합니다.
(google-genai 패키지 사용 - 2025년 11월 이후 권장 SDK)
"""
import logging
import fitz
from typing import Optional

logger = logging.getLogger(__name__)

# Gemini API 가용성 체크 (새 SDK 우선, 기존 SDK 폴백)
GENAI_AVAILABLE = False
LEGACY_SDK = False

try:
    from google import genai
    GENAI_AVAILABLE = True
    logger.info("Using new google-genai SDK")
except ImportError:
    try:
        # 기존 SDK 폴백 (deprecated)
        import google.generativeai as genai_legacy
        GENAI_AVAILABLE = True
        LEGACY_SDK = True
        logger.warning("Using deprecated google-generativeai SDK. Please upgrade to google-genai.")
    except ImportError:
        GENAI_AVAILABLE = False
        logger.warning("No Gemini SDK installed. AI features will be disabled.")


class AIService:
    """
    Gemini API를 사용한 AI 서비스 클래스
    
    사용 예시:
        service = AIService(api_key="your-api-key")
        summary = service.summarize_pdf("document.pdf")
    """
    
    DEFAULT_MODEL = "gemini-flash-latest"
    MAX_TEXT_LENGTH = 30000  # Gemini API 입력 제한
    
    def __init__(self, api_key: str = "", model: str = None):
        """
        Args:
            api_key: Gemini API 키
            model: 사용할 모델명 (기본값: gemini-2.0-flash)
        """
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._configured = False
        self._client = None  # 새 SDK용 클라이언트
        
        if api_key:
            self._configure_api()
    
    def _configure_api(self) -> bool:
        """API 설정 초기화"""
        if not GENAI_AVAILABLE:
            logger.error("Gemini API not available - package not installed")
            return False
            
        if not self._api_key:
            logger.warning("API key not provided")
            return False
            
        try:
            if LEGACY_SDK:
                # 기존 SDK 방식 (deprecated)
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self._api_key)
            else:
                # 새 SDK 방식 (권장)
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            
            self._configured = True
            logger.info(f"Gemini API configured with model: {self._model}")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
            return False
    
    def set_api_key(self, api_key: str) -> bool:
        """
        API 키 설정
        
        Args:
            api_key: Gemini API 키
            
        Returns:
            설정 성공 여부
        """
        self._api_key = api_key
        return self._configure_api()
    
    @property
    def is_available(self) -> bool:
        """AI 서비스 사용 가능 여부"""
        return GENAI_AVAILABLE and self._configured
    
    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = None) -> str:
        """
        PDF에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages: 추출할 최대 페이지 수 (None이면 전체)
            
        Returns:
            추출된 텍스트
        """
        doc = None
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            page_count = len(doc) if max_pages is None else min(len(doc), max_pages)
            
            for i in range(page_count):
                page = doc[i]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"[Page {i+1}]\n{text}")
            
            full_text = "\n\n".join(text_parts)
            
            # 텍스트 길이 제한
            if len(full_text) > self.MAX_TEXT_LENGTH:
                full_text = full_text[:self.MAX_TEXT_LENGTH] + "\n\n[... 텍스트가 잘렸습니다 ...]"
                
            return full_text
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise
        finally:
            if doc:
                doc.close()
    
    def _generate_content(self, prompt: str) -> str:
        """
        API를 통해 콘텐츠 생성 (SDK 버전에 따라 분기)
        
        Args:
            prompt: 프롬프트 텍스트
            
        Returns:
            생성된 텍스트
        """
        if LEGACY_SDK:
            # 기존 SDK 방식
            import google.generativeai as genai_legacy
            model = genai_legacy.GenerativeModel(self._model)
            response = model.generate_content(prompt)
            if response and hasattr(response, 'text') and response.text:
                return response.text
            return ""
        else:
            # 새 SDK 방식
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt
            )
            if response and hasattr(response, 'text') and response.text:
                return response.text
            return ""
    
    def summarize_text(self, text: str, language: str = "ko", 
                       style: str = "concise") -> str:
        """
        텍스트 요약
        
        Args:
            text: 요약할 텍스트
            language: 출력 언어 ("ko", "en")
            style: 요약 스타일 ("concise", "detailed", "bullet")
            
        Returns:
            요약된 텍스트
        """
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and installation.")
        
        if not text.strip():
            return "요약할 텍스트가 없습니다."
        
        # 프롬프트 생성
        lang_instruction = "한국어로" if language == "ko" else "in English"
        
        style_instructions = {
            "concise": "핵심 내용 위주로 1~2 문단으로 간결하게",
            "detailed": "주요 내용을 챕터별로 상세하게",
            "bullet": "핵심 포인트를 불릿 포인트로"
        }
        style_inst = style_instructions.get(style, style_instructions["concise"])
        
        prompt = f"""다음 PDF 문서의 내용을 {lang_instruction} {style_inst} 요약해주세요.

문서 내용:
{text}

요약:"""

        try:
            result = self._generate_content(prompt)
            return result if result else "요약을 생성할 수 없습니다."
                
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise RuntimeError(f"요약 생성 실패: {e}")
    
    def summarize_pdf(self, pdf_path: str, language: str = "ko",
                      style: str = "concise", max_pages: int = None) -> str:
        """
        PDF 파일 요약
        
        Args:
            pdf_path: PDF 파일 경로
            language: 출력 언어 ("ko", "en")
            style: 요약 스타일 ("concise", "detailed", "bullet")
            max_pages: 요약할 최대 페이지 수
            
        Returns:
            요약된 텍스트
        """
        logger.info(f"Summarizing PDF: {pdf_path}")
        
        # 1. 텍스트 추출
        text = self.extract_text_from_pdf(pdf_path, max_pages)
        
        if not text.strip():
            return "PDF에서 추출할 텍스트가 없습니다. (이미지 기반 PDF일 수 있습니다)"
        
        # 2. 요약 생성
        return self.summarize_text(text, language, style)
    
    def ask_about_pdf(self, pdf_path: str, question: str) -> str:
        """
        PDF 내용에 대해 질문
        
        Args:
            pdf_path: PDF 파일 경로
            question: 질문 내용
            
        Returns:
            답변 텍스트
        """
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and installation.")
        
        text = self.extract_text_from_pdf(pdf_path)
        
        prompt = f"""다음 PDF 문서의 내용을 기반으로 질문에 답변해주세요.

문서 내용:
{text}

질문: {question}

답변:"""

        try:
            result = self._generate_content(prompt)
            return result if result else "답변을 생성할 수 없습니다."
                
        except Exception as e:
            logger.error(f"Q&A failed: {e}")
            raise RuntimeError(f"답변 생성 실패: {e}")


# 싱글톤 인스턴스 (선택적 사용)
_ai_service_instance: Optional[AIService] = None

def get_ai_service() -> AIService:
    """전역 AI 서비스 인스턴스 반환"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance
