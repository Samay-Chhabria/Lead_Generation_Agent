"""Minimal JSON-over-HTTP helper for the network LLM provider.

Uses only the standard library so no extra dependency is required to talk to
the OpenAI-compatible FreeLLM Router gateway.
"""

import json
import urllib.error
import urllib.request
from typing import Any

from app.llm.base import LLMError, LLMNetworkError, LLMStatusError


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """POST a JSON payload and return the parsed JSON response.

    Args:
        url: The endpoint URL.
        payload: JSON-serializable request body.
        headers: Optional extra request headers.
        timeout: Request timeout in seconds.

    Returns:
        The parsed JSON response body.

    Raises:
        LLMStatusError: When the provider answers with an HTTP error status.
        LLMNetworkError: When the provider cannot be reached (network failure).
        LLMError: When the provider returns bad data.
    """
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMStatusError(
            f"HTTP {exc.code} from LLM endpoint {url}: {detail[:500]}",
            status_code=exc.code,
        ) from exc
    except urllib.error.URLError as exc:
        raise LLMNetworkError(f"Could not reach LLM endpoint {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise LLMNetworkError(f"Timed out contacting LLM endpoint {url}.") from exc
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMError(f"LLM endpoint {url} returned non-JSON data.") from exc
