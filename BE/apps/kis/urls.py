from django.urls import path

from .views import KisSearchView, KisVideoUploadView


urlpatterns = [
    path("search/", KisSearchView.as_view(), name="kis-search"),
    path("videos/upload/", KisVideoUploadView.as_view(), name="kis-video-upload"),
]
