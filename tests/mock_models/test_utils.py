from django.test import override_settings, TestCase

from django_query_debug.utils import analyze_block, analyze_queryset
from mock_models.models import SimpleModel, SimpleRelatedModel


@override_settings(DEBUG=True)
class TestPatchedDescriptors(TestCase):
    def test_analyze_queryset(self):
        analyze_queryset(SimpleRelatedModel.objects.all())

    def test_analyze_block(self):
        related = SimpleModel.objects.create(name="Simple")
        SimpleRelatedModel.objects.create(name="Test 1")
        SimpleRelatedModel.objects.create(name="Test 2", related_model=related)

        with analyze_block():
            list(SimpleRelatedModel.objects.all())
            list(SimpleRelatedModel.objects.all())

            m = SimpleRelatedModel.objects.get(name="Test 2")
            self.assertEqual(m.related_model.name, "Simple")
