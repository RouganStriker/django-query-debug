from django.test import TestCase

from django_query_debug.utils import analyze_queryset, analyze_block
from mock_models.models import SimpleRelatedModel


class TestMixin(TestCase):
    def test_analyze_queryset(self):
        analyze_queryset(SimpleRelatedModel.objects.filter(related_model=1))

    def test_analyze_block(self):

        with analyze_block():
            SimpleRelatedModel.objects.filter(related_model=1)
