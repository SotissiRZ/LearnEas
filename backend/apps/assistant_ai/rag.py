import io
import re
from typing import Iterable
from django.db import connection
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from pypdf import PdfReader
from apps.catalog.models import Course, Lesson, PDFResource, PDFProduct
from apps.enrollments.models import CourseEnrollment, PDFPurchase
from .models import AIKnowledgeChunk


def chunk_text(text: str, size: int = 1300, overlap: int = 180) -> list[str]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    if len(clean) <= size:
        return [clean]
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + size, len(clean))
        if end < len(clean):
            boundary = max(clean.rfind(". ", start, end), clean.rfind("; ", start, end), clean.rfind("\n", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        piece = clean[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _pdf_text(field_file, max_pages: int = 120) -> str:
    if not field_file:
        return ""
    try:
        with field_file.open("rb") as fh:
            data = fh.read()
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages[:max_pages]:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(pages)
    except Exception:
        return ""


def _replace(source_type: str, source_id: int, title: str, content: str, *, course=None, pdf_product=None,
             instructor=None, is_public=False, source_path="", metadata=None) -> int:
    AIKnowledgeChunk.objects.filter(source_type=source_type, source_id=source_id).delete()
    pieces = chunk_text(content)
    rows = [
        AIKnowledgeChunk(
            source_type=source_type,
            source_id=source_id,
            chunk_index=i,
            title=title[:240],
            content=piece,
            source_path=source_path[:500],
            course=course,
            pdf_product=pdf_product,
            instructor=instructor,
            is_public=is_public,
            metadata=metadata or {},
        )
        for i, piece in enumerate(pieces)
    ]
    if rows:
        AIKnowledgeChunk.objects.bulk_create(rows)
    return len(rows)


def index_course(course: Course) -> int:
    content = "\n".join([
        course.title,
        course.subtitle or "",
        course.description or "",
        "Objectifs : " + "; ".join(course.what_you_will_learn or []),
        "Prérequis : " + "; ".join(course.requirements or []),
        "Public : " + "; ".join(course.target_audience or []),
    ])
    return _replace(
        AIKnowledgeChunk.SourceType.COURSE, course.id, course.title, content,
        course=course, instructor=course.instructor, is_public=course.published,
        source_path=f"/courses/{course.slug}", metadata={"level": course.level, "language": course.language},
    )


def index_lesson(lesson: Lesson) -> int:
    course = lesson.section.course
    content = "\n".join([lesson.title, lesson.description or "", lesson.transcript or ""])
    return _replace(
        AIKnowledgeChunk.SourceType.LESSON, lesson.id,
        f"{course.title} · {lesson.title}", content,
        course=course, instructor=course.instructor,
        is_public=bool(course.published and lesson.is_preview),
        source_path=f"/learn/{course.slug}",
        metadata={"lesson_id": lesson.id, "section": lesson.section.title, "order": lesson.order},
    )


def index_pdf_resource(resource: PDFResource) -> int:
    course = resource.course
    content = "\n".join([resource.title, _pdf_text(resource.file)])
    return _replace(
        AIKnowledgeChunk.SourceType.PDF_RESOURCE, resource.id,
        f"{course.title} · {resource.title}", content,
        course=course, instructor=course.instructor,
        is_public=bool(course.published and resource.is_free_sample),
        source_path=f"/courses/{course.slug}",
        metadata={"page_count": resource.page_count},
    )


def index_pdf_product(product: PDFProduct) -> int:
    file_text = _pdf_text(product.file)
    preview_text = _pdf_text(product.preview_file) if product.preview_file else ""
    content = "\n".join([product.title, product.description or "", file_text or preview_text])
    return _replace(
        AIKnowledgeChunk.SourceType.PDF_PRODUCT, product.id, product.title, content,
        pdf_product=product, instructor=product.instructor,
        is_public=bool(product.published and product.is_free),
        source_path=f"/pdfs/{product.slug}",
        metadata={"page_count": product.page_count, "level": product.level},
    )


def index_object(source_type: str, source_id: int) -> int:
    if source_type == AIKnowledgeChunk.SourceType.COURSE:
        obj = Course.objects.select_related("instructor").filter(pk=source_id).first()
        return index_course(obj) if obj else 0
    if source_type == AIKnowledgeChunk.SourceType.LESSON:
        obj = Lesson.objects.select_related("section__course__instructor", "section").filter(pk=source_id).first()
        return index_lesson(obj) if obj else 0
    if source_type == AIKnowledgeChunk.SourceType.PDF_RESOURCE:
        obj = PDFResource.objects.select_related("course__instructor").filter(pk=source_id).first()
        return index_pdf_resource(obj) if obj else 0
    if source_type == AIKnowledgeChunk.SourceType.PDF_PRODUCT:
        obj = PDFProduct.objects.select_related("instructor").filter(pk=source_id).first()
        return index_pdf_product(obj) if obj else 0
    return 0


def allowed_chunks(user):
    qs = AIKnowledgeChunk.objects.select_related("course", "pdf_product", "instructor")
    if user.role == "admin" or getattr(user, "technical_admin", False):
        return qs
    enrolled_ids = list(CourseEnrollment.objects.filter(user=user).values_list("course_id", flat=True))
    purchased_ids = list(PDFPurchase.objects.filter(user=user).values_list("pdf_product_id", flat=True))
    return qs.filter(
        Q(is_public=True) |
        Q(instructor_id=user.id) |
        Q(course_id__in=enrolled_ids) |
        Q(pdf_product_id__in=purchased_ids)
    )


def _contextual_query(query: str) -> bool:
    text = str(query or "").strip().lower()
    if not text:
        return True
    markers = (
        "ça", "ceci", "cela", "cette leçon", "ce cours", "ce passage", "ici",
        "explique-moi", "explique moi", "résume", "resume", "résume-moi", "résume moi",
        "les dernières minutes", "la partie", "ce pdf", "ce document",
    )
    tokens = re.findall(r"[\wÀ-ÿ-]{3,}", text)
    return len(tokens) <= 4 or any(marker in text for marker in markers)


def retrieve(user, query: str, *, limit: int = 6, course_id: int | None = None, lesson_id: int | None = None,
             pdf_product_id: int | None = None) -> list[AIKnowledgeChunk]:
    """Recherche lexicale + boost contextuel, avec diversité de sources.

    Le contexte de page est très utile pour des questions comme « explique-moi ça »,
    mais ne doit pas polluer une question explicite sans rapport. Les scores calculés
    sont attachés temporairement aux chunks via ``_ai_relevance_score`` pour les
    citations/évaluations, sans modifier le schéma de la base.
    """
    qs = allowed_chunks(user)
    preferred = Q()
    has_preferred = False
    if lesson_id:
        preferred |= Q(source_type=AIKnowledgeChunk.SourceType.LESSON, source_id=lesson_id)
        has_preferred = True
    if course_id:
        preferred |= Q(course_id=course_id)
        has_preferred = True
    if pdf_product_id:
        preferred |= Q(pdf_product_id=pdf_product_id)
        has_preferred = True

    contextual = _contextual_query(query)
    preferred_rows = list(qs.filter(preferred)[: max(limit * 2, 10)]) if has_preferred else []
    tokens = [t for t in re.findall(r"[\wÀ-ÿ-]{3,}", str(query or "").lower()) if len(t) >= 3][:16]

    if connection.vendor == "postgresql" and str(query or "").strip():
        vector = SearchVector("title", weight="A", config="french") + SearchVector("content", weight="B", config="french")
        search = SearchQuery(query, config="french", search_type="websearch")
        ranked = list(
            qs.annotate(rank=SearchRank(vector, search))
            .filter(rank__gt=0.005)
            .order_by("-rank")[: max(limit * 5, 30)]
        )
    else:
        if tokens:
            cond = Q()
            for token in tokens:
                cond |= Q(title__icontains=token) | Q(content__icontains=token)
            ranked = list(qs.filter(cond)[: max(limit * 6, 36)])
        else:
            ranked = []

    candidate_by_id = {row.id: row for row in ranked}
    for row in preferred_rows:
        candidate_by_id.setdefault(row.id, row)
    candidates = list(candidate_by_id.values())

    phrase = str(query or "").strip().lower()

    def score(chunk: AIKnowledgeChunk) -> float:
        title = chunk.title.lower()
        content = chunk.content.lower()
        value = 0.0
        for token in tokens:
            if token in title:
                value += 2.25
            if token in content:
                value += 1.0
        if phrase and len(phrase) >= 8:
            if phrase in title:
                value += 5.0
            elif phrase in content:
                value += 2.0
        value += float(getattr(chunk, "rank", 0) or 0) * 12.0
        same_lesson = bool(lesson_id and chunk.source_type == AIKnowledgeChunk.SourceType.LESSON and chunk.source_id == lesson_id)
        same_course = bool(course_id and chunk.course_id == course_id)
        same_pdf = bool(pdf_product_id and chunk.pdf_product_id == pdf_product_id)
        if contextual:
            if same_lesson:
                value += 9.0
            elif same_course or same_pdf:
                value += 4.0
        else:
            if same_lesson:
                value += 2.0
            elif same_course or same_pdf:
                value += 0.75
        return value

    scored = []
    for chunk in candidates:
        value = score(chunk)
        # Pour une question explicite, ne cite pas une source sans aucun signal lexical.
        # Une question contextuelle peut garder le chunk de la page courante.
        if value <= 0 and not contextual:
            continue
        setattr(chunk, "_ai_relevance_score", round(value, 3))
        scored.append((value, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)

    # Diversifier les résultats : au maximum deux chunks du même objet source.
    selected: list[AIKnowledgeChunk] = []
    per_source: dict[tuple[str, int], int] = {}
    for value, chunk in scored:
        key = (chunk.source_type, chunk.source_id)
        if per_source.get(key, 0) >= 2:
            continue
        selected.append(chunk)
        per_source[key] = per_source.get(key, 0) + 1
        if len(selected) >= limit:
            break
    return selected
