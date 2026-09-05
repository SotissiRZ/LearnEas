# KalanPro v73 — rôle Entreprise / Recruteur

## Parcours public

`/register` propose deux parcours publics : `student` et `employer`. Les rôles privilégiés `admin` et `instructor` ne peuvent pas être auto-attribués par l’API publique.

Lorsqu’un recruteur s’inscrit, KalanPro crée dans la même transaction le compte `User(role=employer)` et son `EmployerProfile(status=pending)`. Il est redirigé vers `/dashboard/employer`.

## Validation

Un profil `pending` peut compléter son identité entreprise mais ne peut publier d’opportunité ni consulter le vivier. L’administration conserve les actions approve/reject/suspend existantes.

## Migration des comptes existants

`opportunities.0002_promote_existing_employers` convertit uniquement les utilisateurs ayant déjà un `EmployerProfile` et encore marqués `student`. Les rôles admin/instructor sont préservés.
