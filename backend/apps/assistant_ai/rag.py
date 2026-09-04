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


def retrieve(user, query: str, *, limit: int = 6, course_id: int | None = None, lesson_id: int | None = None,
             pdf_product_id: int | None = None) -> list[AIKnowledgeChunk]:
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
    preferred_rows = list(qs.filter(preferred)[: max(limit, 6)]) if has_preferred else []

    tokens = [t for t in re.findall(r"[\wÀ-ÿ-]{3,}", query.lower()) if len(t) >= 3][:12]
    if connection.vendor == "postgresql" and query.strip():
        vector = SearchVector("title", weight="A", config="french") + SearchVector("content", weight="B", config="french")
        search = SearchQuery(query, config="french", search_type="websearch")
        ranked = list(qs.annotate(rank=SearchRank(vector, search)).filter(rank__gt=0.01).order_by("-rank")[: max(limit * 3, 12)])
    else:
        if tokens:
            cond = Q()
            for token in tokens:
                cond |= Q(title__icontains=token) | Q(content__icontains=token)
            ranked = list(qs.filter(cond)[: max(limit * 4, 20)])
        else:
            ranked = list(qs[:limit])

    if preferred_rows:
        # Le contexte de la page courante passe en premier, puis les résultats
        # de recherche. Évite les doublons sans altérer le classement global.
        preferred_ids = {row.id for row in preferred_rows}
        ranked = preferred_rows + [row for row in ranked if row.id not in preferred_ids]

    def score(chunk: AIKnowledgeChunk) -> float:
        text = f"{chunk.title} {chunk.content}".lower()
        value = sum(1.0 for t in tokens if t in text)
        if lesson_id and chunk.source_type == AIKnowledgeChunk.SourceType.LESSON and chunk.source_id == lesson_id:
            value += 8
        if course_id and chunk.course_id == course_id:
            value += 4
        if pdf_product_id and chunk.pdf_product_id == pdf_product_id:
            value += 4
        value += float(getattr(chunk, "rank", 0) or 0) * 10
        return value

    ranked.sort(key=score, reverse=True)
    return ranked[:limit]
