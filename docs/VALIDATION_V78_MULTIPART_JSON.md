# Validation v78 — multipart JSON du profil entreprise

## Problème reproduit

Après suppression du `deepcopy` multipart, DRF recevait encore un `MultiValueDict`. Les champs `values`, `benefits` et `hiring_regions` étaient décodés en listes Python puis interprétés une seconde fois comme valeurs HTML de `JSONField`, d’où « La valeur doit être un JSON valide ».

## Correction

Le helper `_shallow_mutable_input()` transforme désormais un `QueryDict`/`MultiValueDict` en dictionnaire Python ordinaire via `items()`. Cela conserve les fichiers uploadés par référence, évite le `deepcopy` et permet aux `JSONField` de recevoir directement les listes déjà décodées.

Le test multipart emploie un `TemporaryUploadedFile` contenant un PNG 2×2 valide et vérifie `logo`, `banner`, `values`, `benefits` et `hiring_regions`.

Aucune migration n’est requise.
