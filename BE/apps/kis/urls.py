from django.urls import path

from .views import KISSearchView


urlpatterns = [path("search/",KISSearchView.as_view(),name="kis-search",),]