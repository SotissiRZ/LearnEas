from django.urls import path
from .views import GlobalSearchView, RecommendationView, SearchSuggestionsView

urlpatterns = [
    path("search/", GlobalSearchView.as_view(), name="global-search"),
    path("search/suggestions/", SearchSuggestionsView.as_view(), name="search-suggestions"),
    path("recommendations/", RecommendationView.as_view(), name="recommendations"),
]
