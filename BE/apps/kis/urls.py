from django.urls import path

from .views import (KisDatasetAssetView, KisSearchView, KisVideoUploadView,)


urlpatterns = [
    path("search/",KisSearchView.as_view(),name="kis-search",),
    path("videos/upload/",KisVideoUploadView.as_view(),name="kis-video-upload",),
    path("assets/<path:asset_path>",KisDatasetAssetView.as_view(),name="kis-dataset-asset",),
]
