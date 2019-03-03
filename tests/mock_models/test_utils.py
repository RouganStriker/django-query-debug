from django.test import override_settings, TestCase
from testfixtures import LogCapture

from django_query_debug.utils import analyze_block, analyze_queryset
from mock_models.models import SimpleRelatedModel


@override_settings(DEBUG=True)
class TestPatchedDescriptors(TestCase):
    def test_analyze_queryset(self):
        analyze_queryset(SimpleRelatedModel.objects.all())

    def test_analyze_block(self):
        with analyze_block():
            list(SimpleRelatedModel.objects.all())
            list(SimpleRelatedModel.objects.all())
