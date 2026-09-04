from celery import shared_task
from .rag import index_object


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def index_catalog_object(self, source_type: str, source_id: int):
    return index_object(source_type, source_id)
