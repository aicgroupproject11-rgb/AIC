from collections.abc import Callable
from importlib import import_module
from typing import Any

from django.conf import settings


class SearchServiceUnavailable(RuntimeError):
    """The algorithm team's search module is absent or cannot be imported."""


class SearchServiceFailed(RuntimeError):
    """The search module exists but failed while processing a request."""


def _load_search_function() -> Callable[..., list[dict[str, Any]]]:
    """Load the algorithm function only when an API request needs it.

    The default path is intentionally outside the API app. The algorithm/data
    team can provide this module later without changing the API contract.
    """

    dotted_path = getattr(settings, "KIS_SEARCH_FUNCTION", "search_engine.kis.search",)
    module_path, separator, function_name = dotted_path.rpartition(".")

    if not separator:
        raise SearchServiceUnavailable("KIS_SEARCH_FUNCTION phải có dạng 'package.module.function'.")

    try:
        module = import_module(module_path)
        search_function = getattr(module, function_name)
    except (ImportError, AttributeError) as exc:
        raise SearchServiceUnavailable("Module tìm kiếm KIS chưa được kết nối với API.") from exc

    if not callable(search_function):
        raise SearchServiceUnavailable("KIS_SEARCH_FUNCTION không phải là một hàm.")

    return search_function


def search_kis(*, query: str, collection_ids: list[str], top_k: int,) -> list[dict[str, Any]]:

    search_function = _load_search_function()

    try:
        results = search_function(
            query=query,
            collection_ids=collection_ids,
            top_k=top_k,
        )
    except (FileNotFoundError, TimeoutError, ValueError) as exc:
        raise SearchServiceFailed(str(exc)) from exc

    if not isinstance(results, list):
        raise SearchServiceFailed("Search module phải trả về list[dict].")

    return results
