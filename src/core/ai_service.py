"""
AI Service for PDF Master v4.2
Gemini API를 활용한 PDF 요약 서비스를 제공합니다.
(google-genai 패키지 사용 - 2025년 11월 이후 권장 SDK)
"""
import logging
import fitz
import time
from typing import Optional
from functools import wraps

# AI 관련 상수 import
try:
    from .constants import AI_MAX_TEXT_LENGTH, AI_DEFAULT_TIMEOUT, AI_MAX_RETRIES, AI_BASE_DELAY, AI_MAX_DELAY
except ImportError:
    # 독립 실행 시 폴백
    AI_MAX_TEXT_LENGTH = 30000
    AI_DEFAULT_TIMEOUT = 30
    AI_MAX_RETRIES = 3
    AI_BASE_DELAY = 1.0
    AI_MAX_DELAY = 30.0

logger = logging.getLogger(__name__)

# =====================================================================
# Gemini API SDK 가용성 체크
# =====================================================================
# 공식 패키지: google-genai (pip install google-genai)
# Import 방식: from google import genai
# 참고: google-generativeai는 2025년 11월 30일 deprecated됨

GENAI_AVAILABLE = False
LEGACY_SDK = False
GENAI_CLIENT = None  # SDK 클라이언트 참조

try:
    from google import genai
    GENAI_AVAILABLE = True
    GENAI_CLIENT = genai
    logger.info("google-genai SDK loaded successfully")
except ImportError:
    try:
        # deprecated SDK 폴백 (호환성 유지)
        import google.generativeai as genai_legacy
        GENAI_AVAILABLE = True
        LEGACY_SDK = True
        GENAI_CLIENT = genai_legacy
        logger.warning(
            "Using deprecated google-generativeai SDK. "
            "Please upgrade: pip install google-genai"
        )
    except ImportError:
        GENAI_AVAILABLE = False
        logger.warning(
            "No Gemini SDK installed. AI features disabled. "
            "Install with: pip install google-genai"
        )


class AIServiceError(Exception):
    """AI 서비스 관련 기본 예외"""
    pass


class APIKeyError(AIServiceError):
    """API 키 관련 오류"""
    pass


class APITimeoutError(AIServiceError):
    """API 타임아웃 오류"""
    pass


class APIRateLimitError(AIServiceError):
    """API 호출 제한 오류"""
    pass


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    지수 백오프를 사용한 재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
    """
    import random  # v4.5: jitter를 위한 import
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        # v4.5: 랜덤 jitter 추가 (Thundering Herd 방지)
                        jitter = random.uniform(0, 1)
                        delay = min(base_delay * (2 ** attempt) + jitter, max_delay)
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
                        raise
                except Exception as e:
                    # 재시도 불가능한 오류는 즉시 발생
                    error_str = str(e).lower()
                    if 'rate limit' in error_str or 'quota' in error_str:
                        raise APIRateLimitError(f"API 호출 제한에 도달했습니다: {e}")
                    elif 'api key' in error_str or 'invalid' in error_str or 'authentication' in error_str:
                        raise APIKeyError(f"API 키가 유효하지 않습니다: {e}")
                    raise
            raise last_exception
        return wrapper
    return decorator


class AIService:
    """
    Gemini API를 사용한 AI 서비스 클래스
    
    사용 예시:
        service = AIService(api_key="your-api-key")
        summary = service.summarize_pdf("document.pdf")
    """
    
    DEFAULT_MODEL = "gemini-flash-latest"
    MAX_TEXT_LENGTH = AI_MAX_TEXT_LENGTH  # constants.py에서 가져옴
    DEFAULT_TIMEOUT = AI_DEFAULT_TIMEOUT  # constants.py에서 가져옴
    MAX_RETRIES = AI_MAX_RETRIES  # constants.py에서 가져옴
    
    def __init__(self, api_key: str = "", model: str = None, timeout: int = None):
        """
        Args:
            api_key: Gemini API 키
            model: 사용할 모델명 (기본값: gemini-flash-latest)
            timeout: API 호출 타임아웃 (초, 기본값: 30)
        """
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._timeout = timeout or self.DEFAULT_TIMEOUT
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
        
        # API 키 형식 기본 검증
        if not self._validate_api_key_format(self._api_key):
            logger.error("Invalid API key format")
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
    
    def _validate_api_key_format(self, api_key: str) -> bool:
        """
        API 키 형식 기본 검증
        
        Args:
            api_key: 검증할 API 키
            
        Returns:
            형식이 유효한지 여부
        """
        if not api_key or not isinstance(api_key, str):
            return False
        
        # 최소 길이 확인 (Gemini API 키는 보통 39자)
        if len(api_key) < 20:
            return False
        
        # 공백 없음 확인
        if ' ' in api_key or '\n' in api_key or '\t' in api_key:
            return False
        
        return True
    
    def validate_api_key(self) -> tuple[bool, str]:
        """
        API 키 유효성 실제 검증 (API 호출로 확인)
        
        Returns:
            (성공 여부, 메시지) 튜플
        """
        if not GENAI_AVAILABLE:
            return False, "Gemini SDK가 설치되지 않았습니다."
        
        if not self._api_key:
            return False, "API 키가 설정되지 않았습니다."
        
        if not self._validate_api_key_format(self._api_key):
            return False, "API 키 형식이 올바르지 않습니다."
        
        try:
            # 간단한 테스트 요청으로 API 키 확인
            test_prompt = "Hi"
            if LEGACY_SDK:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self._api_key)
                model = genai_legacy.GenerativeModel(self._model)
                response = model.generate_content(test_prompt)
            else:
                from google import genai
                client = genai.Client(api_key=self._api_key)
                response = client.models.generate_content(
                    model=self._model,
                    contents=test_prompt
                )
            
            if response:
                return True, "API 키가 유효합니다."
            return False, "API 응답을 받지 못했습니다."
            
        except Exception as e:
            error_str = str(e).lower()
            if 'api key' in error_str or 'invalid' in error_str or 'authentication' in error_str:
                return False, "API 키가 유효하지 않습니다."
            elif 'rate limit' in error_str or 'quota' in error_str:
                return False, "API 호출 제한에 도달했습니다. 잠시 후 다시 시도하세요."
            else:
                return False, f"API 연결 오류: {e}"
    
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
            current_length = 0  # v4.5: 메모리 최적화 - 누적 길이 추적
            
            for i in range(page_count):
                page = doc[i]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"[Page {i+1}]\n{text}")
                    current_length += len(text_parts[-1])
                    
                    # v4.5: 최대 길이 초과 시 조기 종료 (메모리 절약)
                    if current_length > self.MAX_TEXT_LENGTH:
                        logger.info(f"Text extraction stopped at page {i+1} due to length limit")
                        break
            
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
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _generate_content(self, prompt: str) -> str:
        """
        API를 통해 콘텐츠 생성 (SDK 버전에 따라 분기)
        
        Args:
            prompt: 프롬프트 텍스트
            
        Returns:
            생성된 텍스트
            
        Raises:
            APITimeoutError: 타임아웃 발생 시
            APIKeyError: API 키 오류 시
            APIRateLimitError: Rate limit 초과 시
        """
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        import concurrent.futures
        
        def api_call():
            if LEGACY_SDK:
                # 기존 SDK 방식
                import google.generativeai as genai_legacy
                model = genai_legacy.GenerativeModel(self._model)
                response = model.generate_content(prompt)
                if response and hasattr(response, 'text') and response.text:
                    return response.text
            else:
                # 새 SDK 방식
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt
                )
                if response and hasattr(response, 'text') and response.text:
                    return response.text
            return ""

        # ThreadPoolExecutor를 with문으로 사용하여 리소스 보장
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(api_call)
                # 타임아웃 설정
                result = future.result(timeout=self._timeout)
                return result
            except TimeoutError:
                logger.error(f"API call timed out after {self._timeout} seconds")
                # 타임아웃 시 future 취소 시도
                future.cancel()
                raise APITimeoutError(f"API 호출이 {self._timeout}초 후 타임아웃되었습니다.")
            except Exception as e:
                logger.error(f"API call error: {e}")
                raise e
    
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
            
        Raises:
            RuntimeError: AI 서비스 사용 불가 시
            APITimeoutError: 타임아웃 발생 시
            APIKeyError: API 키 오류 시
            APIRateLimitError: Rate limit 초과 시
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
        except APITimeoutError:
            raise RuntimeError("요약 생성 시간이 초과되었습니다. 잠시 후 다시 시도하세요.")
        except APIKeyError as e:
            raise RuntimeError(str(e))
        except APIRateLimitError as e:
            raise RuntimeError(str(e))
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
    
    def ask_about_pdf(self, pdf_path: str, question: str,
                      conversation_history: list = None) -> str:
        """
        PDF 내용에 대해 질문 (v4.5: 대화 맥락 지원)
        
        Args:
            pdf_path: PDF 파일 경로
            question: 질문 내용
            conversation_history: 이전 대화 기록 [{"role": "user"|"assistant", "content": "..."}]
            
        Returns:
            답변 텍스트
        """
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and installation.")
        
        text = self.extract_text_from_pdf(pdf_path)
        
        # v4.5: 대화 기록 포맷팅
        history_context = ""
        if conversation_history:
            history_parts = []
            for entry in conversation_history[-5:]:  # 최근 5개 대화만 사용
                role = "사용자" if entry.get("role") == "user" else "AI"
                history_parts.append(f"{role}: {entry.get('content', '')}")
            if history_parts:
                history_context = "\n\n이전 대화:\n" + "\n".join(history_parts)
        
        prompt = f"""다음 PDF 문서의 내용을 기반으로 질문에 답변해주세요.

문서 내용:
{text}{history_context}

질문: {question}

답변:"""

        try:
            result = self._generate_content(prompt)
            return result if result else "답변을 생성할 수 없습니다."
        except APITimeoutError:
            raise RuntimeError("답변 생성 시간이 초과되었습니다. 잠시 후 다시 시도하세요.")
        except APIKeyError as e:
            raise RuntimeError(str(e))
        except APIRateLimitError as e:
            raise RuntimeError(str(e))
        except Exception as e:
            logger.error(f"Q&A failed: {e}")
            raise RuntimeError(f"답변 생성 실패: {e}")
    
    def extract_keywords(self, pdf_path: str, max_keywords: int = 10, 
                         language: str = "ko") -> list:
        """
        PDF에서 핵심 키워드 추출
        
        Args:
            pdf_path: PDF 파일 경로
            max_keywords: 추출할 최대 키워드 수 (기본값: 10)
            language: 출력 언어 ("ko", "en")
            
        Returns:
            키워드 리스트
        """
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and installation.")
        
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            return []
        
        lang_instruction = "한국어로" if language == "ko" else "in English"
        
        prompt = f"""다음 PDF 문서에서 가장 중요한 핵심 키워드/주제를 추출해주세요.

규칙:
1. 최대 {max_keywords}개의 키워드만 추출
2. 각 키워드는 한 줄에 하나씩
3. 키워드만 출력 (번호나 설명 없이)
4. {lang_instruction} 작성

문서 내용:
{text}

키워드:"""

        try:
            result = self._generate_content(prompt)
            if not result:
                return []
            
            # 결과 파싱 - 각 줄을 키워드로 처리
            keywords = []
            for line in result.strip().split('\n'):
                keyword = line.strip()
                # 번호 제거 (예: "1. 키워드" -> "키워드")
                if keyword and len(keyword) > 0:
                    # 번호 패턴 제거
                    import re
                    keyword = re.sub(r'^[\d]+[\.\)\-\s]+', '', keyword).strip()
                    if keyword and keyword not in keywords:
                        keywords.append(keyword)
                        if len(keywords) >= max_keywords:
                            break
            
            return keywords
            
        except APITimeoutError:
            raise RuntimeError("키워드 추출 시간이 초과되었습니다.")
        except APIKeyError as e:
            raise RuntimeError(str(e))
        except APIRateLimitError as e:
            raise RuntimeError(str(e))
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            raise RuntimeError(f"키워드 추출 실패: {e}")

# 싱글톤 인스턴스 (선택적 사용)
_ai_service_instance: Optional[AIService] = None
_ai_service_lock = __import__('threading').Lock()  # v4.5: 스레드 안전성

def get_ai_service() -> AIService:
    """전역 AI 서비스 인스턴스 반환 (스레드 안전)"""
    global _ai_service_instance
    if _ai_service_instance is None:
        with _ai_service_lock:
            # Double-check locking pattern
            if _ai_service_instance is None:
                _ai_service_instance = AIService()
    return _ai_service_instance
