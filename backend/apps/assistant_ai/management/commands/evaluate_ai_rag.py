from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models import User
from apps.assistant_ai.evaluation import seed_evaluation_cases, run_evaluation


class Command(BaseCommand):
    help = "Évalue la pertinence du RAG KalanPro avec un jeu de questions déterministe (Hit@K)."

    def add_arguments(self, parser):
        parser.add_argument("--seed-demo", action="store_true", help="Crée des cas d'évaluation à partir des contenus indexés existants.")
        parser.add_argument("--user-email", default="", help="Compte utilisé pour les permissions. Par défaut : premier admin.")
        parser.add_argument("--top-k", type=int, default=6)
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        if options["seed_demo"]:
            self.stdout.write(f"Cas d'évaluation créés : {seed_evaluation_cases(options['limit'])}")
        email = (options.get("user_email") or "").strip()
        user = User.objects.filter(email__iexact=email).first() if email else User.objects.filter(role="admin").order_by("id").first()
        if not user:
            raise CommandError("Aucun utilisateur d'évaluation trouvé. Utilisez --user-email ou créez un admin.")
        result = run_evaluation(user, top_k=options["top_k"], limit=options["limit"])
        if not result["total"]:
            raise CommandError("Aucun cas d'évaluation. Lancez avec --seed-demo ou ajoutez des cas dans Django Admin.")
        for row in result["cases"]:
            marker = "PASS" if row["passed"] else "FAIL"
            self.stdout.write(f"[{marker}] #{row['id']} rank={row['rank'] or '-'} · {row['question']}")
        self.stdout.write(self.style.SUCCESS(
            f"RAG KalanPro : Hit@{result['top_k']}={result['hit_rate']:.1f}% ({result['passed']}/{result['total']}) · MRR={result['mrr']:.3f}"
        ))
