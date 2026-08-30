from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from .models import ChatMessage


class ChatPermissionsTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice_chat', email='alice-chat@example.com', password='passpass123')
        self.bob = User.objects.create_user(username='bob_chat', email='bob-chat@example.com', password='passpass123')
        self.charlie = User.objects.create_user(username='charlie_chat', email='charlie-chat@example.com', password='passpass123')
        self.message = ChatMessage.objects.create(sender=self.alice, recipient=self.bob, content='Bonjour')

    def test_third_party_cannot_read_message(self):
        self.client.force_authenticate(self.charlie)
        response = self.client.get(f'/api/chat/messages/{self.message.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_only_recipient_can_mark_message_read(self):
        self.client.force_authenticate(self.alice)
        denied = self.client.post(f'/api/chat/messages/{self.message.id}/mark-read/', {}, format='json')
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.bob)
        allowed = self.client.post(f'/api/chat/messages/{self.message.id}/mark-read/', {}, format='json')
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)

    def test_messages_are_not_editable_or_deletable(self):
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.patch(f'/api/chat/messages/{self.message.id}/', {'content': 'modifié'}, format='json').status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.delete(f'/api/chat/messages/{self.message.id}/').status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
