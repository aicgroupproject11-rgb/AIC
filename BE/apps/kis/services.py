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


def get_search_function():
    path = getattr(settings, "KIS_SEARCH_FUNCTION", "search_engine.kis.search")

    try:
        module_name, function_name = path.rsplit(".", 1)
        module = import_module(module_name)
        return getattr(module, function_name)
    except (ValueError, ImportError, AttributeError, OSError) as exc:
        raise SearchServiceUnavailable(
            f"Không load được search engine: {path}"
        ) from exc


def search_kis(
    query: str,
    collection_ids: list[str],
    top_k: int,
):
    """Nối API với hàm search của team Search Engine."""
    clean_query, keys, collection_tags = parse_query(query)

    if not clean_query:
        raise InvalidSearchRequest(
            "Query cần ít nhất một từ khóa tìm kiếm."
        )

    final_collection_ids = merge_collection_ids(
        collection_ids,
        collection_tags,
    )

    search = get_search_function()

    try:
        results = search(
            query=clean_query,
            collection_ids=final_collection_ids,
            top_k=top_k,
        )
    except Exception as exc:
        if isinstance(exc, (FileNotFoundError, ImportError, ModuleNotFoundError, OSError), ) or exc.__class__.__name__ == "SearchServiceUnavailable":
            raise SearchServiceUnavailable(str(exc) or "Search index hoặc dữ liệu KIS chưa sẵn sàng.") from exc

        logger.exception("KIS search failed")
        raise SearchServiceFailed(str(exc) or "Search engine gặp lỗi.") from exc

    if not isinstance(results, list):
        raise SearchServiceFailed("Search engine phải trả về một list kết quả.")

    parsed_info = {
        "keys": keys,
        "effective_collection_ids": final_collection_ids,
    }

    return parsed_info, results
