from django.urls import path

from .views import (
    KisDatasetAssetView,
    KisSearchInspectView,
    KisSearchView,
    KisVideoUploadView,
)


urlpatterns = [
    path("search/", KisSearchView.as_view(), name="kis-search"),
    path(
        "search/inspect/",
        KisSearchInspectView.as_view(),
        name="kis-search-inspect",
    ),
    path(
        "videos/upload/",
        KisVideoUploadView.as_view(),
        name="kis-video-upload",
    ),
    path(
        "assets/<path:asset_path>",
        KisDatasetAssetView.as_view(),
        name="kis-dataset-asset",
    ),
]
