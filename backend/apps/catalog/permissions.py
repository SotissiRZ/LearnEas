from rest_framework import permissions


def _resolve_owner(obj):
    """Retrouve l'instructeur propriétaire d'un objet, quelle que soit sa profondeur
    dans le graphe de relations (Course, Section -> Course, Lesson -> Section -> Course,
    PDFResource -> Course, PDFProduct direct...)."""
    if hasattr(obj, "instructor"):
        return obj.instructor
    if hasattr(obj, "course") and obj.course is not None:
        return obj.course.instructor
    if hasattr(obj, "section") and obj.section is not None:
        return obj.section.course.instructor
    if hasattr(obj, "formation") and obj.formation is not None:
        return obj.formation.instructor
    return None


class IsInstructorOrAdmin(permissions.BasePermission):
    """Seuls les instructeurs (sur leur propre contenu) et les admins peuvent écrire."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role in ("instructor", "admin")

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = _resolve_owner(obj)
        return request.user.role == "admin" or owner == request.user


class IsInstructorOrAdminOnly(permissions.BasePermission):
    """Endpoint de gestion : jamais public, même en GET.

    Les fichiers protégés sont servis au public uniquement via les serializers imbriqués
    qui appliquent les règles d'inscription/achat.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ("instructor", "admin")

    def has_object_permission(self, request, view, obj):
        owner = _resolve_owner(obj)
        return request.user.role == "admin" or owner == request.user


class IsAdminRoleOrReadOnly(permissions.BasePermission):
    """Lecture publique, écriture réservée au rôle admin LearnEas."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "admin"
        )
