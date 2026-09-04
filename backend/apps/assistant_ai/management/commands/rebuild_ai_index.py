from django.core.management.base import BaseCommand
from apps.catalog.models import Course, Lesson, PDFResource, PDFProduct
from apps.assistant_ai.models import AIKnowledgeChunk
from apps.assistant_ai.rag import index_course, index_lesson, index_pdf_resource, index_pdf_product


class Command(BaseCommand):
    help = "Reconstruit la base de connaissances RAG de KalanPro AI."

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true")
        parser.add_argument("--if-empty", action="store_true", help="Ne reconstruit que si aucun chunk n'existe.")

    def handle(self, *args, **options):
        if options.get("if_empty") and AIKnowledgeChunk.objects.exists():
            if not options["quiet"]:
                self.stdout.write("Index IA déjà présent, aucune reconstruction.")
            return
        AIKnowledgeChunk.objects.all().delete()
        total = 0
        for course in Course.objects.select_related("instructor").all():
            total += index_course(course)
        for lesson in Lesson.objects.select_related("section__course__instructor", "section").all():
            total += index_lesson(lesson)
        for resource in PDFResource.objects.select_related("course__instructor").all():
            total += index_pdf_resource(resource)
        for product in PDFProduct.objects.select_related("instructor").all():
            total += index_pdf_product(product)
        if not options["quiet"]:
            self.stdout.write(self.style.SUCCESS(f"Index IA reconstruit : {total} chunks."))
