class SearchServiceUnavailable(RuntimeError):
    """The search index or model is not ready to serve queries."""


class IndexBuildError(RuntimeError):
    """The input dataset is inconsistent and an index cannot be built safely."""
