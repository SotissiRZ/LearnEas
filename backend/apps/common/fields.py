"""
Champs DRF renvoyant des URLs de fichiers/images RELATIVES (ex: "/media/courses/x.mp4")
plutôt qu'absolues (ex: "http://backend:8000/media/courses/x.mp4").

Pourquoi : en environnement Docker, le backend est contacté par DEUX chemins différents :
  - depuis le NAVIGATEUR (via nginx) : Host = "localhost" (ou le domaine public)
  - depuis le SERVEUR Next.js en SSR (réseau interne Docker) : Host = "backend:8000"
Le comportement par défaut de DRF (FileField/ImageField) construit une URL absolue à partir
du Host de la requête REÇUE PAR DJANGO — ce qui donnerait des URLs "http://backend:8000/media/..."
totalement injoignables depuis le navigateur de l'utilisateur final quand la donnée a été
récupérée en SSR.

En renvoyant une URL relative, on laisse le NAVIGATEUR la résoudre par rapport à l'origine de
la page qu'il affiche (toujours la bonne, que la donnée vienne du SSR ou d'un fetch client) —
et nginx sait déjà servir /media/ correctement dans les deux cas.
"""
from rest_framework import serializers


class RelativeImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None
        try:
            return value.url
        except (AttributeError, ValueError):
            return None


class RelativeFileField(serializers.FileField):
    def to_representation(self, value):
        if not value:
            return None
        try:
            return value.url
        except (AttributeError, ValueError):
            return None
