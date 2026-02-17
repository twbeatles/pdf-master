"""
Undo/Redo Manager for PDF Master v4.0
작업 히스토리를 관리하여 실행 취소/다시 실행 기능을 제공합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ActionRecord:
    """실행된 작업을 기록하는 데이터 클래스"""
    action_type: str  # 작업 유형 (예: "merge", "delete_pages", "rotate")
    description: str  # 사용자에게 표시할 설명
    timestamp: datetime = field(default_factory=datetime.now)
    before_state: dict = field(default_factory=dict)  # 작업 전 상태
    after_state: dict = field(default_factory=dict)   # 작업 후 상태
    undo_callback: Optional[Callable] = None  # 실행 취소 콜백
    redo_callback: Optional[Callable] = None  # 다시 실행 콜백


class UndoManager:
    """
    작업 히스토리를 관리하는 Undo/Redo 매니저
    
    사용 예시:
        manager = UndoManager(max_history=50)
        manager.push("delete_pages", "3페이지 삭제", before, after, undo_fn, redo_fn)
        manager.undo()  # 마지막 작업 취소
        manager.redo()  # 취소된 작업 다시 실행
    """
    
    def __init__(self, max_history: int = 50):
        """
        Args:
            max_history: 저장할 최대 히스토리 개수 (메모리 관리)
        """
        self._undo_stack: list[ActionRecord] = []
        self._redo_stack: list[ActionRecord] = []
        self._max_history = max_history
        self._enabled = True
        
    @property
    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        return self._enabled and len(self._undo_stack) > 0
    
    @property
    def can_redo(self) -> bool:
        """다시 실행 가능 여부"""
        return self._enabled and len(self._redo_stack) > 0
    
    @property
    def undo_description(self) -> str:
        """다음 실행 취소 작업 설명"""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return ""
    
    @property
    def redo_description(self) -> str:
        """다음 다시 실행 작업 설명"""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return ""
    
    def push(self, action_type: str, description: str, 
             before_state: dict = None, after_state: dict = None,
             undo_callback: Callable = None, redo_callback: Callable = None) -> None:
        """
        새 작업을 히스토리에 추가
        
        Args:
            action_type: 작업 유형 식별자
            description: 사용자에게 표시할 작업 설명
            before_state: 작업 전 상태 (선택적)
            after_state: 작업 후 상태 (선택적)
            undo_callback: 실행 취소 시 호출할 함수
            redo_callback: 다시 실행 시 호출할 함수
        """
        if not self._enabled:
            return
            
        record = ActionRecord(
            action_type=action_type,
            description=description,
            before_state=before_state or {},
            after_state=after_state or {},
            undo_callback=undo_callback,
            redo_callback=redo_callback
        )
        
        self._undo_stack.append(record)
        
        # 새 작업 추가 시 redo 스택 초기화
        self._redo_stack.clear()
        
        # 최대 히스토리 개수 유지
        while len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
            
        logger.debug(f"Pushed action: {action_type} - {description}")
    
    def undo(self) -> Optional[ActionRecord]:
        """
        마지막 작업 실행 취소
        
        Returns:
            취소된 ActionRecord 또는 None
        """
        if not self.can_undo:
            logger.warning("Nothing to undo")
            return None
            
        record = self._undo_stack.pop()
        self._redo_stack.append(record)
        
        if record.undo_callback:
            try:
                record.undo_callback(record.before_state)
                logger.info(f"Undo: {record.description}")
            except Exception as e:
                logger.error(f"Undo callback failed: {e}")
                # 실패 시 스택 복구
                self._redo_stack.pop()
                self._undo_stack.append(record)
                raise
        
        return record
    
    def redo(self) -> Optional[ActionRecord]:
        """
        취소된 작업 다시 실행
        
        Returns:
            다시 실행된 ActionRecord 또는 None
        """
        if not self.can_redo:
            logger.warning("Nothing to redo")
            return None
            
        record = self._redo_stack.pop()
        self._undo_stack.append(record)
        
        if record.redo_callback:
            try:
                record.redo_callback(record.after_state)
                logger.info(f"Redo: {record.description}")
            except Exception as e:
                logger.error(f"Redo callback failed: {e}")
                # 실패 시 스택 복구
                self._undo_stack.pop()
                self._redo_stack.append(record)
                raise
        
        return record
    
    def clear(self) -> None:
        """모든 히스토리 삭제"""
        self._undo_stack.clear()
        self._redo_stack.clear()
        logger.debug("Undo history cleared")
    
    def set_enabled(self, enabled: bool) -> None:
        """Undo/Redo 기능 활성화/비활성화"""
        self._enabled = enabled
        
    def get_undo_history(self) -> list[str]:
        """실행 취소 가능한 작업 목록 반환"""
        return [record.description for record in reversed(self._undo_stack)]
    
    def get_redo_history(self) -> list[str]:
        """다시 실행 가능한 작업 목록 반환"""
        return [record.description for record in reversed(self._redo_stack)]
