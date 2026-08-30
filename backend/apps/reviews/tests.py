from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import Category, Course, Section, Lesson
from apps.enrollments.models import CourseEnrollment


class ReviewAndDiscussionPermissionsTests(APITestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(username='review_teacher', email='review-teacher@example.com', password='passpass123', role=User.Role.INSTRUCTOR)
        self.student = User.objects.create_user(username='review_student', email='review-student@example.com', password='passpass123', role=User.Role.STUDENT)
        self.outsider = User.objects.create_user(username='review_outsider', email='review-outsider@example.com', password='passpass123', role=User.Role.STUDENT)
        category = Category.objects.create(name='Reviews')
        self.course = Course.objects.create(instructor=self.instructor, category=category, title='Cours privé avis', description='Test', price=Decimal('20.00'), published=True)
        section = Section.objects.create(course=self.course, title='Module', order=1)
        self.lesson = Lesson.objects.create(section=section, title='Leçon', order=1)
        CourseEnrollment.objects.create(user=self.student, course=self.course)

    def test_outsider_cannot_post_review(self):
        self.client.force_authenticate(self.outsider)
        response = self.client.post('/api/reviews/reviews/', {'course': self.course.id, 'rating': 5, 'comment': 'Non'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enrolled_student_can_post_review(self):
        self.client.force_authenticate(self.student)
        response = self.client.post('/api/reviews/reviews/', {'course': self.course.id, 'rating': 5, 'comment': 'Très bien'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_private_discussion_is_not_visible_to_outsider(self):
        self.client.force_authenticate(self.student)
        created = self.client.post('/api/reviews/comments/', {'lesson': self.lesson.id, 'content': 'Question privée'}, format='json')
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.client.force_authenticate(self.outsider)
        listing = self.client.get('/api/reviews/comments/')
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        rows = listing.data.get('results', listing.data) if isinstance(listing.data, dict) else listing.data
        self.assertEqual(len(rows), 0)
