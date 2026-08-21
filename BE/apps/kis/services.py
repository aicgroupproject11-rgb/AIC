import logging
import re
from importlib import import_module

from django.conf import settings

logger = logging.getLogger(__name__)


class InvalidSearchRequest(ValueError):
    pass


class SearchServiceUnavailable(RuntimeError):
    pass


class SearchServiceFailed(RuntimeError):
    pass


COLLECTION_TAG_PATTERN = re.compile(r"#(L\d+)\b", re.IGNORECASE)


def parse_query(query: str) -> tuple[str, list[str], list[str]]:
    """Tách câu query thành text tìm kiếm, keywords và collection tags."""
    collection_ids = [
        match.group(1).upper()
        for match in COLLECTION_TAG_PATTERN.finditer(query)
    ]

    clean_query = COLLECTION_TAG_PATTERN.sub(" ", query)
    clean_query = re.sub(r"#(?=\w)", "", clean_query)
    clean_query = " ".join(clean_query.split())
    keys = clean_query.split()

    return clean_query, keys, collection_ids


def merge_collection_ids(
    collection_ids: list[str],
    collection_tags: list[str],
) -> list[str]:
    result = []

    for collection_id in collection_ids + collection_tags:
        collection_id = collection_id.strip().upper()
        if collection_id and collection_id not in result:
            result.append(collection_id)

    return result


def get_engine_function(setting_name: str, default_path: str):
    path = getattr(settings, setting_name, default_path)

    try:
        module_name, function_name = path.rsplit(".", 1)
        module = import_module(module_name)
        return getattr(module, function_name)
    except (ValueError, ImportError, AttributeError, OSError) as exc:
        raise SearchServiceUnavailable(
            f"Không load được search engine: {path}"
        ) from exc


def get_search_function():
    return get_engine_function(
        "KIS_SEARCH_FUNCTION",
        "search_engine.kis.search",
    )


def get_inspect_function():
    return get_engine_function(
        "KIS_INSPECT_FUNCTION",
        "search_engine.kis.inspect",
    )


def prepare_query(
    query: str,
    collection_ids: list[str],
) -> tuple[str, dict]:
    clean_query, keys, collection_tags = parse_query(query)

    if not clean_query:
        raise InvalidSearchRequest(
            "Query cần ít nhất một từ khóa tìm kiếm."
        )

    final_collection_ids = merge_collection_ids(
        collection_ids,
        collection_tags,
    )

    return clean_query, {
        "keys": keys,
        "effective_collection_ids": final_collection_ids,
    }


def call_engine(function, *, query, collection_ids, top_k):
    try:
        return function(
            query=query,
            collection_ids=collection_ids,
            top_k=top_k,
        )
    except Exception as exc:
        unavailable_errors = (
            FileNotFoundError,
            ImportError,
            ModuleNotFoundError,
            OSError,
        )
        if (
            isinstance(exc, unavailable_errors)
            or exc.__class__.__name__ == "SearchServiceUnavailable"
        ):
            raise SearchServiceUnavailable(
                str(exc) or "Search index hoặc dữ liệu KIS chưa sẵn sàng."
            ) from exc

        logger.exception("KIS search engine failed")
        raise SearchServiceFailed(str(exc) or "Search engine gặp lỗi.") from exc


def search_kis(
    query: str,
    collection_ids: list[str],
    top_k: int,
):
    """Nối API với hàm search của team Search Engine."""
    clean_query, parsed_info = prepare_query(query, collection_ids)
    results = call_engine(
        get_search_function(),
        query=clean_query,
        collection_ids=parsed_info["effective_collection_ids"],
        top_k=top_k,
    )

    if not isinstance(results, list):
        raise SearchServiceFailed("Search engine phải trả về một list kết quả.")

    return parsed_info, results


def inspect_kis(
    query: str,
    collection_ids: list[str],
    top_k: int,
):
    """Trả về routing trace để giải thích một truy vấn, không trả keyframe."""
    clean_query, parsed_info = prepare_query(query, collection_ids)
    trace = call_engine(
        get_inspect_function(),
        query=clean_query,
        collection_ids=parsed_info["effective_collection_ids"],
        top_k=top_k,
    )

    if not isinstance(trace, dict):
        raise SearchServiceFailed("Search inspect phải trả về một object.")

    return parsed_info, trace
