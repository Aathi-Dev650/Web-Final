from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User


class AuthenticationApiTests(TestCase):
    def test_register_creates_a_logged_in_account(self):
        response = self.client.post('/api/disease/auth/register/', {'username': 'farmer', 'password': 'safe-password-1'})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username='farmer').exists())
        self.assertEqual(self.client.get('/api/disease/auth/me/').json()['username'], 'farmer')

    def test_history_requires_login(self):
        self.assertEqual(self.client.get('/api/disease/history/').status_code, 403)

    def test_detection_validates_the_upload_before_database_access(self):
        user = User.objects.create_user('farmer', password='safe-password-1')
        self.client.force_login(user)
        response = self.client.post('/api/disease/create/', {'crop': 'tomato', 'symptom': 'leaf_spots'})
        self.assertEqual(response.status_code, 400)

    def test_detection_reports_when_trained_model_is_missing(self):
        user = User.objects.create_user('grower', password='safe-password-1')
        self.client.force_login(user)
        image = SimpleUploadedFile('leaf.jpg', b'not-a-real-image', content_type='image/jpeg')
        response = self.client.post('/api/disease/create/', {'image': image})
        self.assertEqual(response.status_code, 503)
        self.assertIn('Disease model is not installed', response.json()['detail'])

# Create your tests here.
