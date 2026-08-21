from pathlib import Path
import pickle
import numpy as np
from sklearn.decomposition import PCA
from rtree import index as rtree_index

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "data" / "search_index"
PCA_DIM = 16 


class SearchServiceUnavailable(RuntimeError):
    """Runtime error indicating that the search service is unavailable, usually because the index has not been built yet."""


class SearchIndex:
    def __init__(self, pca, ids, collection_ids, reduced, full_vectors):
        self.pca = pca
        self.ids = ids                 
        self.collection_ids = collection_ids  
        self.reduced = reduced      
        self.full_vectors = full_vectors  
        self.rtree = self._build_rtree()

    def _build_rtree(self):
        p = rtree_index.Property()
        p.dimension = self.reduced.shape[1]
        idx = rtree_index.Index(properties=p)
        for i, vec in enumerate(self.reduced):
            bbox = tuple(vec) + tuple(vec)  
            idx.insert(i, bbox)
        return idx

    def candidates(self, query_reduced: np.ndarray, k: int = 200) -> list[int]:
        bbox = tuple(query_reduced) + tuple(query_reduced)
        return list(self.rtree.nearest(bbox, num_results=k))

    def save(self, path: Path = INDEX_DIR):
        path.mkdir(parents=True, exist_ok=True)
        with open(path / "pca.pkl", "wb") as f:
            pickle.dump(self.pca, f)
        np.save(path / "reduced.npy", self.reduced)
        np.save(path / "full_vectors.npy", self.full_vectors)
        with open(path / "ids.pkl", "wb") as f:
            pickle.dump({"ids": self.ids, "collection_ids": self.collection_ids}, f)

    @classmethod
    def load(cls, path: Path = INDEX_DIR) -> "SearchIndex":
        pca_file = path / "pca.pkl"
        if not pca_file.exists():
            raise SearchServiceUnavailable(
                f"Have not built index at {path}. Run: python search_engine/build_index.py"
            )
        with open(pca_file, "rb") as f:
            pca = pickle.load(f)
        reduced = np.load(path / "reduced.npy")
        full_vectors = np.load(path / "full_vectors.npy")
        with open(path / "ids.pkl", "rb") as f:
            meta = pickle.load(f)
        return cls(pca, meta["ids"], meta["collection_ids"], reduced, full_vectors)


def build_index(ids: list[str], collection_ids: list[str], full_vectors: np.ndarray) -> SearchIndex:
    pca = PCA(n_components=PCA_DIM, random_state=42)
    reduced = pca.fit_transform(full_vectors).astype("float32")
    return SearchIndex(pca, ids, collection_ids, reduced, full_vectors)

_index_cache = None

def get_index() -> SearchIndex:
    global _index_cache
    if _index_cache is None:
        _index_cache = SearchIndex.load()
    return _index_cache