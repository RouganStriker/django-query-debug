import logging

from django.db import models
from django.db.models import ManyToManyField
from django.db.models.base import ModelBase
from django.db.models.fields.related import RelatedField, ManyToManyRel, ForeignObjectRel
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from six import with_metaclass

from django_query_debug.utils import FieldUsageSession, print_green, print_yellow

logger = logging.getLogger('query_debug')


class UsageTrackingDescriptor(object):
    def __init__(self, field_name, default_value):
        self.field_name = field_name
        self.value = default_value

    def __get__(self, instance, owner):
        if not FieldUsageSession.has_current or not FieldUsageSession.current.disable_tracking:
            instance.get_field_usage()[self.field_name] += 1

        if hasattr(self.value, "__get__"):
            return self.value.__get__(instance, owner)

        return self.value

    def __set__(self, instance, value):
        if hasattr(self.value, "__set__"):
            self.value.__set__(instance, value)
        else:
            self.value = value


class FieldUsageTrackerMeta(ModelBase):
    """
    Metaclass that adds field usage tracking stats.
    """

    def setup_field_usage_stats(cls):
        """
        Wrap existing model fields with a custom descriptor to track field access.

        If the model gets re-used, the stats will also carry-over.
        """
        usage_stats = getattr(cls, "_field_usage", {})

        for f in cls._meta.get_fields():
            field_name = getattr(f, "attname", f.name)
            default_value = getattr(cls, field_name, None)

            if not hasattr(cls, field_name):
                if isinstance(f, ManyToManyField):
                    default_value = ManyToManyDescriptor(f.remote_field)
                elif isinstance(f, ManyToManyRel):
                    default_value = ManyToManyDescriptor(f, reverse=True)
                elif isinstance(f, ForeignObjectRel):
                    default_value = f.remote_field.related_accessor_class(f)

            if isinstance(f, RelatedField) and not isinstance(f, ManyToManyField):
                # Related fields have two attributes, with _id and without.
                # Add a descriptor to the field without _id.
                if f.name not in usage_stats:
                    usage_stats[f.name] = 0

                model_descriptor = getattr(cls, f.name, f.forward_related_accessor_class(f))
                setattr(cls, f.name, UsageTrackingDescriptor(f.name,
                                                             default_value=model_descriptor))

            setattr(cls, field_name, UsageTrackingDescriptor(field_name,
                                                             default_value=default_value))

            if field_name not in usage_stats:
                usage_stats[field_name] = 0

        # Add field usage dict
        setattr(cls, "_field_usage", usage_stats)

    def __call__(cls, *args, **kwargs):
        cls.setup_field_usage_stats()

        return super(FieldUsageTrackerMeta, cls).__call__(*args, **kwargs)


class FieldUsageMixin(with_metaclass(FieldUsageTrackerMeta)):
    def get_field_usage(self):
        # Field created in metaclass
        return self._field_usage

    def reset_field_usage(self):
        self._field_usage = {
            field_name: 0
            for field_name in self._field_usage.keys()
        }

    @staticmethod
    def _indented_msg(msg, indent_level):
        return "{}{}".format(' ' * indent_level, msg)

    def display_field_usage(self, show_related=True):
        with FieldUsageSession(disable_tracking=True):
            logger.info("Displaying field usage for `{}`:".format(self))
            self._display_field_usage(indent_level=2, show_related=show_related)

    def _display_field_usage(self, indent_level=0, show_related=True, parent_models=None):
        """
        Display field usage data.

        Will also display field usage data from related fields that also
        support field usage tracking.
        """
        if parent_models is None:
            parent_models = set()
        parent_models = parent_models.union({self})

        sorted_keys = sorted(self._field_usage.keys())

        for field_name in sorted_keys:
            usage_count = self._field_usage.get(field_name)
            msg = self._indented_msg('{}: {}'.format(field_name, usage_count), indent_level)

            if usage_count > 0:
                print_green(msg)
            else:
                logger.info(msg)

            field = self._meta.get_field(field_name)

            if not show_related or usage_count == 0 or field.related_model is None:
                continue
            if field_name.endswith("_id"):
                # Skip the related ID field; stats will be displayed from the non ID version
                continue
            if not hasattr(field.related_model, '_display_field_usage'):
                msg = "{} does not support field usage tracking".format(field.related_model.__name__)
                print_yellow(self._indented_msg(msg, indent_level + 2))
                continue

            # Display related field usage
            related_field_name = field_name

            if hasattr(self, field.get_cache_name()):
                related_field_name = field.get_cache_name()

            related_field = getattr(self, related_field_name)

            if related_field in parent_models:
                # Prevent recursion from cyclic relations
                print_yellow(self._indented_msg("Skipping cyclic relation", indent_level + 2))
                return

            if isinstance(related_field, models.Manager):
                for index, related_many_object in enumerate(related_field.all()):
                    msg = "Object {}:".format(index)
                    logger.info(self._indented_msg(msg, indent_level + 2))
                    related_many_object._display_field_usage(indent_level=indent_level + 4,
                                                             show_related=show_related,
                                                             parent_models=parent_models)
            elif isinstance(related_field, models.Model):
                related_field._display_field_usage(indent_level=indent_level + 2,
                                                   show_related=show_related,
                                                   parent_models=parent_models)
