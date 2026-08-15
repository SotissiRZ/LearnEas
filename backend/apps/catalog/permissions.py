from rest_framework import permissions


class IsInstructorOrAdmin(permissions.BasePermission):
    """Seuls les instructeurs (sur leur propre contenu) et les admins peuvent écrire."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role in ("instructor", "admin")

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "instructor", None) or getattr(getattr(obj, "course", None), "instructor", None)
        return request.user.role == "admin" or owner == request.user
