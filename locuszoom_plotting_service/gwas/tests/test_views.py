from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import signals
from django.test import TestCase
from django.urls import reverse
import factory


from .factories import (
    UserFactory, GwasFactory
)


# TODO: Add permissions tests for all views
# TODO: find a way to keep test runs from cluttering FS with 0B files; temp folder maybe?
class TestOverviewPermissions(TestCase):
    @classmethod
    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def setUpTestData(cls):
        cls.user_owner = user1 = UserFactory()
        cls.user_other = user2 = UserFactory()

        # Create fake studies with no data, that will render anyway
        sample_file = SimpleUploadedFile('fictional.txt', content='')

        cls.study_private = GwasFactory(owner=user1, is_public=False, raw_gwas_file=sample_file)
        cls.study_public = GwasFactory(owner=user2, is_public=True, raw_gwas_file=sample_file)

    def test_owner_can_see_private_study(self):
        self.client.force_login(self.user_owner)
        response = self.client.get(reverse('gwas:overview', args=[self.study_private.pk]))
        self.assertContains(response, 'still being processed', status_code=200)

    def test_other_user_cannot_see_private_study(self):
        self.client.force_login(self.user_other)
        response = self.client.get(reverse('gwas:overview', args=[self.study_private.pk]))
        self.assertNotContains(response, 'still being processed', status_code=403)
