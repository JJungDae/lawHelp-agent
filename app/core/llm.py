from typing import Any, Dict, Iterator, List, Optional

from app.core.config import settings


DEFAULT_SYSTEM_PROMPT = "너는 법제처 생활법령 백문백답 기반 생활법률 안내 챗봇이다."
UPSTAGE_API_BASE = "https://api.upstage.ai/v1"


class LLMError(Exception):
    """LLM 호출 실패를 상위 계층에서 공통으로 처리하기 위한 예외."""


def generate_text(prompt: str, system: Optional[str] = None) -> str:
    """Upstage Solar 답변을 문자열로 반환한다."""
    try:
        response = _completion(
            messages=_build_messages(prompt=prompt, system=system),
            stream=False,
        )
        content = _extract_message_content(response)
    except Exception as exc:
        raise LLMError("LLM text generation failed.") from exc

    if not content:
        raise LLMError("LLM returned an empty response.")
    return content


def stream_text(prompt: str, system: Optional[str] = None) -> Iterator[str]:
    """Upstage Solar 답변 조각을 순차적으로 반환한다."""
    try:
        response = _completion(
            messages=_build_messages(prompt=prompt, system=system),
            stream=True,
        )
        for chunk in response:
            text = _extract_stream_text(chunk)
            if text:
                yield text
    except Exception as exc:
        raise LLMError("LLM text streaming failed.") from exc


def _completion(messages: List[Dict[str, str]], stream: bool) -> Any:
    if not settings.upstage_api_key:
        raise LLMError("UPSTAGE_API_KEY is not configured.")

    try:
        from litellm import completion
    except ModuleNotFoundError as exc:
        raise LLMError("litellm is not installed.") from exc

    return completion(
        model=_litellm_model_name(settings.llm_model),
        messages=messages,
        api_key=settings.upstage_api_key,
        api_base=UPSTAGE_API_BASE,
        stream=stream,
    )


def _build_messages(prompt: str, system: Optional[str]) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system or DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def _litellm_model_name(model: str) -> str:
    if model.startswith("openai/"):
        return model
    if model.startswith("upstage/"):
        return f"openai/{model.split('/', 1)[1]}"
    return f"openai/{model}"


def _extract_message_content(response: Any) -> str:
    choice = response["choices"][0] if isinstance(response, dict) else response.choices[0]
    message = choice["message"] if isinstance(choice, dict) else choice.message
    content = message["content"] if isinstance(message, dict) else message.content
    return content.strip() if content else ""


def _extract_stream_text(chunk: Any) -> str:
    choice = chunk["choices"][0] if isinstance(chunk, dict) else chunk.choices[0]
    delta = choice["delta"] if isinstance(choice, dict) else choice.delta
    content = delta.get("content") if isinstance(delta, dict) else getattr(delta, "content", None)
    return content or ""


# TODO: Day3에서는 call_with_retry() 기반 재시도 정책을 구현하지 않는다.
# TODO: Day3에서는 classify_text() 기반 LLM 분류를 구현하지 않는다.
