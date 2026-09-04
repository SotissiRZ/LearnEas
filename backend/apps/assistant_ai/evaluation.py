from django.utils import timezone
from apps.catalog.models import Course, Lesson, PDFProduct
from .models import AIEvaluationCase, AIKnowledgeChunk
from .rag import retrieve


def seed_evaluation_cases(limit: int = 45) -> int:
    created = 0
    per_type = max(3, min(15, max(limit, 9) // 3))
    lessons = Lesson.objects.exclude(transcript="").select_related("section__course").order_by("id")[:per_type]
    for lesson in lessons:
        _, was_created = AIEvaluationCase.objects.get_or_create(
            question=f"Que contient la leçon « {lesson.title} » ?",
            expected_source_type=AIKnowledgeChunk.SourceType.LESSON,
            expected_source_id=lesson.id,
            defaults={"notes": f"Cours : {lesson.section.course.title}"},
        )
        created += int(was_created)
    for course in Course.objects.filter(published=True).order_by("id")[:per_type]:
        _, was_created = AIEvaluationCase.objects.get_or_create(
            question=f"Quels sont les objectifs du cours « {course.title} » ?",
            expected_source_type=AIKnowledgeChunk.SourceType.COURSE,
            expected_source_id=course.id,
        )
        created += int(was_created)
    for pdf in PDFProduct.objects.filter(published=True).order_by("id")[:per_type]:
        _, was_created = AIEvaluationCase.objects.get_or_create(
            question=f"Que contient le document « {pdf.title} » ?",
            expected_source_type=AIKnowledgeChunk.SourceType.PDF_PRODUCT,
            expected_source_id=pdf.id,
        )
        created += int(was_created)
    return created


def run_evaluation(user, *, top_k: int = 6, limit: int = 50) -> dict:
    top_k = max(1, min(int(top_k), 12))
    limit = max(1, min(int(limit), 200))
    cases = list(AIEvaluationCase.objects.filter(enabled=True).order_by("id")[:limit])
    passed = 0
    reciprocal_rank = 0.0
    rows = []
    for case in cases:
        results = retrieve(user, case.question, limit=top_k)
        rank = None
        for index, row in enumerate(results, start=1):
            if row.source_type == case.expected_source_type and row.source_id == case.expected_source_id:
                rank = index
                break
        ok = rank is not None
        case.last_passed = ok
        case.last_rank = rank
        case.last_run_at = timezone.now()
        case.save(update_fields=["last_passed", "last_rank", "last_run_at"])
        if ok:
            passed += 1
            reciprocal_rank += 1.0 / rank
        rows.append({"id": case.id, "question": case.question, "passed": ok, "rank": rank})
    total = len(cases)
    return {
        "top_k": top_k,
        "total": total,
        "passed": passed,
        "hit_rate": round(passed / total * 100, 1) if total else None,
        "mrr": round(reciprocal_rank / total, 3) if total else None,
        "cases": rows,
    }
