import logging
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.catalog.models import Course, Lesson, PDFResource, PDFProduct
from .models import AIKnowledgeChunk
from .rag import index_object

logger = logging.getLogger(__name__)

MODEL_TYPES = {
    Course: AIKnowledgeChunk.SourceType.COURSE,
    Lesson: AIKnowledgeChunk.SourceType.LESSON,
    PDFResource: AIKnowledgeChunk.SourceType.PDF_RESOURCE,
    PDFProduct: AIKnowledgeChunk.SourceType.PDF_PRODUCT,
}


def _schedule(source_type: str, source_id: int):
    if getattr(settings, "AI_INDEX_ASYNC", False):
        from .tasks import index_catalog_object
        try:
            index_catalog_object.delay(source_type, source_id)
        except Exception:
            # En production, ne jamais parser un PDF lourd dans la requête HTTP
            # simplement parce que le broker est momentanément indisponible.
            logger.exception("Impossible de planifier l’indexation IA %s:%s", source_type, source_id)
        return
    index_object(source_type, source_id)


@receiver(post_save, sender=Course)
@receiver(post_save, sender=Lesson)
@receiver(post_save, sender=PDFResource)
@receiver(post_save, sender=PDFProduct)
def index_saved_content(sender, instance, **kwargs):
    source_type = MODEL_TYPES[sender]
    transaction.on_commit(lambda: _schedule(source_type, instance.pk))


@receiver(post_delete, sender=Course)
@receiver(post_delete, sender=Lesson)
@receiver(post_delete, sender=PDFResource)
@receiver(post_delete, sender=PDFProduct)
def delete_indexed_content(sender, instance, **kwargs):
    AIKnowledgeChunk.objects.filter(source_type=MODEL_TYPES[sender], source_id=instance.pk).delete()
