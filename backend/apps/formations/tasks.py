from celery import shared_task


@shared_task
def refresh_cohort_waitlists():
    from .cohorts import refresh_waitlist
    from .models import InteractiveFormation, FormationKind, FormationStatus

    count = 0
    ids = InteractiveFormation.objects.filter(
        kind=FormationKind.COHORT,
        published=True,
        status=FormationStatus.SCHEDULED,
        waitlist_entries__isnull=False,
    ).values_list("id", flat=True).distinct()
    for formation_id in ids.iterator():
        count += len(refresh_waitlist(formation_id))
    return count


@shared_task
def generate_recurring_mentorship_slots():
    from django.db.models import Q
    from django.utils import timezone
    from .mentorship import generate_rule_slots
    from .models import MentorshipAvailabilityRule

    created = 0
    # Inclure aussi les règles désactivées/non publiées qui possèdent encore des
    # créneaux futurs actifs, afin que le worker puisse nettoyer les disponibilités
    # devenues obsolètes même après une modification faite depuis l'admin Django.
    rules = MentorshipAvailabilityRule.objects.filter(
        Q(is_active=True, offering__published=True)
        | Q(generated_slots__is_active=True, generated_slots__starts_at__gt=timezone.now())
    ).select_related("offering").distinct()
    for rule in rules.iterator():
        created += generate_rule_slots(rule, horizon_days=45)
    return created
