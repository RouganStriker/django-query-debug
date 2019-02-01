from django.db import models

from django_query_debug.mixins import QueryAnalysisModelMixin


class SimpleModel(models.Model, QueryAnalysisModelMixin):
    class Meta(object):
        app_label = 'mock_models'

    name = models.CharField(max_length=255)


class SimpleRelatedModel(models.Model, QueryAnalysisModelMixin):
    class Meta(object):
        app_label = 'mock_models'

    name = models.CharField(max_length=255)
    related_model = models.ForeignKey(SimpleModel, on_delete=models.CASCADE)
