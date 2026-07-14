from typing import Any, Dict, Iterator, List, Optional

from app.core.config import settings
from app.core.observability import start_observation, summarize_messages


DEFAULT_SYSTEM_PROMPT = "너는 법제처 생활법령 백문백답 기반 생활법률 안내 챗봇이다."
UPSTAGE_API_BASE = "https://api.upstage.ai/v1"


class LLMError(Exception):
    """LLM 호출 실패를 상위 계층에서 공통으로 처리하기 위한 예외."""


def generate_text(prompt: str, system: Optional[str] = None) -> str:
    """Upstage Solar 응답을 문자열로 반환한다."""
    messages = _build_messages(prompt=prompt, system=system)

    with start_observation(
        name="generation",
        as_type="generation",
        input={"messages": summarize_messages(messages)},
        metadata={"provider": "upstage", "stream": False},
        model=settings.llm_model,
        model_parameters={"stream": False},
    ) as observation:
        try:
            response = _completion(
                messages=messages,
                stream=False,
            )
            content = _extract_message_content(response)
        except Exception as exc:
            observation.update(level="ERROR", status_message=type(exc).__name__)
            raise LLMError("LLM text generation failed.") from exc

        if not content:
            observation.update(level="ERROR", status_message="empty_response")
            raise LLMError("LLM returned an empty response.")

        observation.update(output=content, usage_details=_extract_usage_details(response))
        return content


def stream_text(prompt: str, system: Optional[str] = None) -> Iterator[str]:
    """Upstage Solar 응답 조각을 순차적으로 반환한다."""
    messages = _build_messages(prompt=prompt, system=system)

    with start_observation(
        name="generation",
        as_type="generation",
        input={"messages": summarize_messages(messages)},
        metadata={"provider": "upstage", "stream": True},
        model=settings.llm_model,
        model_parameters={"stream": True},
    ) as observation:
        try:
            response = _completion(
                messages=messages,
                stream=True,
            )
            chunks = []
            for chunk in response:
                text = _extract_stream_text(chunk)
                if text:
                    chunks.append(text)
                    yield text
            observation.update(output="".join(chunks))
        except Exception as exc:
            observation.update(level="ERROR", status_message=type(exc).__name__)
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


def _extract_usage_details(response: Any) -> Optional[dict[str, int]]:
    usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
    if not usage:
        return None

    usage_key_map = {
        "prompt_tokens": "input",
        "input_tokens": "input",
        "completion_tokens": "output",
        "output_tokens": "output",
        "total_tokens": "total",
    }
    usage_details = {}
    for source_key, target_key in usage_key_map.items():
        value = usage.get(source_key) if isinstance(usage, dict) else getattr(usage, source_key, None)
        if isinstance(value, int):
            usage_details[target_key] = value
    return usage_details or None


# TODO: Day3에서 call_with_retry() 기반 재시도 정책은 구현하지 않는다.
# TODO: Day3에서 classify_text() 기반 LLM 분류는 구현하지 않는다.
