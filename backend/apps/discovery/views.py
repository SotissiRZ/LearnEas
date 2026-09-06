from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.opportunities.services import employer_has_talent_pool_access
from .services import approved_employer_for, normalize_text, parse_types, recommendations_for, search_all, suggestions


class GlobalSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = str(request.query_params.get("q") or "").strip()[:120]
        if query and len(normalize_text(query)) < 2:
            return Response({"detail": "Saisissez au moins 2 caractères."}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user if request.user.is_authenticated else None
        employer = approved_employer_for(user) if user else None
        allow_talents = bool(employer and employer_has_talent_pool_access(employer))
        types = parse_types(request.query_params.get("types"), allow_talents=allow_talents)
        try:
            limit = max(1, min(int(request.query_params.get("limit", 8)), 12))
        except (TypeError, ValueError):
            limit = 8
        payload = search_all(query=query, types=types, limit=limit, user=user)
        payload["available_types"] = parse_types(None, allow_talents=allow_talents)
        return Response(payload)


class SearchSuggestionsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = str(request.query_params.get("q") or "").strip()[:120]
        return Response({"query": query, "suggestions": suggestions(query, limit=8, user=request.user if request.user.is_authenticated else None)})


class RecommendationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            limit = max(1, min(int(request.query_params.get("limit", 6)), 12))
        except (TypeError, ValueError):
            limit = 6
        user = request.user if request.user.is_authenticated else None
        return Response(recommendations_for(user, limit=limit))
