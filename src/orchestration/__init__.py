"""
Модуль для оркестрации процесса обработки патентов и документов

Публичные функции:
- create_patent_orchestrator: Создает оркестратор для обработки патентов
- create_document_orchestrator: Создает оркестратор для обработки документов
"""

from .orchestrator import create_patent_orchestrator, create_document_orchestrator

__all__ = ["create_patent_orchestrator", "create_document_orchestrator"]