from .services import search_kis


def process_fe_command(query: str, collection_ids: list[str], top_k: int,):

    return search_kis(query=query, collection_ids=collection_ids, top_k=top_k,)
