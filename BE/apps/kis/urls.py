from django.urls import path

from .views import KisSearchView


urlpatterns = [
    path("search/", KisSearchView.as_view(), name="kis-search"),
]
