from django.db import models

from django_query_debug.mixins import FieldUsageMixin


class SimpleModel(models.Model):
    class Meta(object):
        app_label = 'mock_models'

    name = models.CharField(max_length=255)


class SimpleRelatedModel(models.Model):
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


class UntrackedSimpleModel(models.Model):
    name = models.CharField(max_length=255)


class FieldTrackedSimpleModel(FieldUsageMixin, models.Model):
    name = models.CharField(max_length=255)


class FieldTrackedRelatedModel(FieldUsageMixin, models.Model):
    name = models.CharField(max_length=255)
    related_model = models.ForeignKey(FieldTrackedSimpleModel,
                                      on_delete=models.CASCADE,
                                      related_name="reverse_related_model",
                                      null=True)
    many_models = models.ManyToManyField(FieldTrackedSimpleModel,
                                         related_name="reverse_many_models")
    one_to_one_model = models.OneToOneField(FieldTrackedSimpleModel,
                                            on_delete=models.CASCADE,
                                            related_name="reverse_one_to_one_model",
                                            null=True)
    untracked_model = models.ForeignKey(UntrackedSimpleModel,
                                        on_delete=models.CASCADE,
                                        related_name="reverse_related_model",
                                        null=True)


class BaseModel(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        abstract = True


class BaseModelWithMixin(FieldUsageMixin, models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        abstract = True


class ExtendedChildModel(FieldUsageMixin, BaseModel):
    related_model = models.ForeignKey("SimpleModel",
                                      on_delete=models.CASCADE,
                                      related_name="reverse_extended_related_model",
                                      null=True)


class InheritedChildModel(BaseModelWithMixin):
    related_model = models.ForeignKey("SimpleModel",
                                      on_delete=models.CASCADE,
                                      related_name="reverse_inherited_related_model",
                                      null=True)
