from django.test import TestCase
from django.urls import reverse


from .factories import (
    UserFactory, AnalysisInfoFactory
)


class TestOverviewPermissions(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_owner = user1 = UserFactory()
        cls.user_other = user2 = UserFactory()

        # Create fake studies with no data, that will render anyway
        cls.study_private = AnalysisInfoFactory(owner=user1, is_public=False)
        cls.study_public = AnalysisInfoFactory(owner=user2, is_public=True)

    def tearDown(self):
        self.client.logout()

    def test_owner_can_see_private_study(self):
        self.client.force_login(self.user_owner)

        response = self.client.get(reverse('gwas:overview', args=[self.study_private.slug]))
        self.assertContains(response, 'still being processed', status_code=200,
                            msg_prefix='User should be able to see their own study')

        response = self.client.get(reverse('gwas:overview', args=[self.study_public.slug]))
        self.assertContains(response, 'still being processed', status_code=200,
                            msg_prefix='Public study should be visible')

    def test_other_user_cannot_see_private_study(self):
        self.client.force_login(self.user_other)
        response = self.client.get(reverse('gwas:overview', args=[self.study_private.slug]))
        self.assertNotContains(response, 'still being processed', status_code=403,
                               msg_prefix='Private study should not be visible')

    def test_public_study_no_auth_required(self):
        response = self.client.get(reverse('gwas:overview', args=[self.study_public.slug]))
        self.assertEqual(response.status_code, 200)

    def test_private_study_requires_auth(self):
        response = self.client.get(reverse('gwas:overview', args=[self.study_private.slug]))
        self.assertEqual(response.status_code, 403, 'User must be logged in')

        self.client.force_login(self.user_other)
        response = self.client.get(reverse('gwas:overview', args=[self.study_private.slug]))
        self.assertEqual(response.status_code, 403, 'Only owner can see a private study')
