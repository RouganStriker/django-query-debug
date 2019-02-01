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
    related_model = models.ForeignKey(SimpleModel,
                                      on_delete=models.CASCADE,
                                      related_name="reverse_related_model",
                                      null=True)
    many_models = models.ManyToManyField(SimpleModel, related_name="reverse_many_models")
    one_to_one_model = models.OneToOneField(SimpleModel,
                                            on_delete=models.CASCADE,
                                            related_name="reverse_one_to_one_model",
                                            null=True)


class ChildSimpleModel(SimpleModel):
    parent = models.OneToOneField(SimpleModel,
                                  on_delete=models.CASCADE,
                                  parent_link=True,
                                  related_name="child_model")
