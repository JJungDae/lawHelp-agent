from enum import Enum


EXACT_DISTANCE_THRESHOLD = 0.45
RELATED_DISTANCE_THRESHOLD = 0.59


class AnswerRoute(str, Enum):
    OUT_OF_SCOPE = "out_of_scope"
    GROUNDED_RAG = "grounded_rag"
    RELATED_HYBRID = "related_hybrid"
    LLM_ONLY = "llm_only"
    ERROR = "error"


class DomainGuardrailResult(str, Enum):
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    UNCERTAIN = "uncertain"
