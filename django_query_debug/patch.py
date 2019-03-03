import logging

from django.conf import settings
from django.db.models.base import Model
from django.db.models.fields import related_descriptors
from django.db.models.fields.related_descriptors import (ForwardManyToOneDescriptor,
                                                         ForwardOneToOneDescriptor,
                                                         ReverseOneToOneDescriptor)

from django_query_debug.utils import TracebackLogger

logger = logging.getLogger('query_debug')


class PatchDjangoDescriptors(object):
    """
    Monkey patch the builtin Django fields and descriptors
    to add query warnings.
    """

    def __init__(self):
        # The ForwardOneToOneDescriptor does not need to be patched because
        # it will call ForwardManyToOneDescriptor if a query is made.

        if not getattr(settings, "ENABLE_QUERY_WARNINGS", False):
            # Query Warnings disabled, don't apply patch
            return

        self._patch_with_warnings(ReverseOneToOneDescriptor,
                                  "get_queryset",
                                  self.get_warning_for_reverse_one_to_one_descriptor)
        self._patch_with_warnings(Model, "refresh_from_db", self.get_warning_for_deferred_fields)
        self._patch_with_warnings(ForwardManyToOneDescriptor,
                                  "get_object",
                                  self.get_warning_for_many_to_one_descriptor)

        self.monkey_patch_many_to_many_factory()
        self.monkey_patch_reverse_many_to_one_factory()

    @staticmethod
    def _patch_with_warnings(obj, original_method_name, get_warning):
        """
        Patch an object's method to conditionally display a warning message and traceback.
        """
        original_method = getattr(obj, original_method_name)

        def wrapper(*args, **kwargs):
            warning_message = get_warning(*args, **kwargs)

            if warning_message and getattr(settings, "ENABLE_QUERY_WARNINGS", False):
                logger.warning(warning_message)
                TracebackLogger.print_traceback()

            return original_method(*args, **kwargs)

        setattr(obj, original_method_name, wrapper)

    @staticmethod
    def get_warning_for_reverse_one_to_one_descriptor(descriptor, *args, **kwargs):
        return "Accessing uncached reverse OneToOne field {}.{}".format(descriptor.related.model.__name__,
                                                                        descriptor.related.related_name)

    @staticmethod
    def get_warning_for_deferred_fields(instance, using=None, fields=None):
        """Accessing deferred fields will call refresh_from_db for that field."""
        if fields is None:
            # Explicit call to refresh all fields
            return None

        deferred_fields = set(fields).intersection(instance.get_deferred_fields())

        if deferred_fields:
            return "Accessing deferred field(s) {}".format(", ".join(deferred_fields))

        return None

    @staticmethod
    def get_warning_for_many_to_one_descriptor(instance, model_instance):
        if isinstance(instance, ForwardOneToOneDescriptor):
            # Triggered via a super call from ForwardOneToOneDescriptor if a query is made
            descriptor_type = "OneToOne"
        else:
            descriptor_type = "ManyToOne"

        return "Accessing uncached {} field {}.{}".format(descriptor_type,
                                                          model_instance.__class__.__name__,
                                                          instance.field.name)

    def monkey_patch_many_to_many_factory(self):
        original_create_forward_many_to_many_manager = related_descriptors.create_forward_many_to_many_manager

        def get_warning_message(manager):
            prefetch_cache = getattr(manager.instance, "_prefetched_objects_cache", None)

            if not prefetch_cache or manager.prefetch_cache_name not in prefetch_cache:
                return "Accessing uncached ManyToMany field {}.{}".format(manager.instance.__class__.__name__,
                                                                          manager.prefetch_cache_name)

        def create_forward_many_to_many_manager(*args, **kwargs):
            related_manager = original_create_forward_many_to_many_manager(*args, **kwargs)

            self._patch_with_warnings(related_manager, "get_queryset", get_warning_message)

            return related_manager

        related_descriptors.create_forward_many_to_many_manager = create_forward_many_to_many_manager

    def monkey_patch_reverse_many_to_one_factory(self):
        original_create_reverse_many_to_one_manager = related_descriptors.create_reverse_many_to_one_manager

        def get_warning_message(manager):
            prefetch_cache = getattr(manager.instance, "_prefetched_objects_cache", None)

            if not prefetch_cache or manager.field.related_query_name() not in prefetch_cache:
                return "Accessing uncached reverse ManyToOne field {}.{}".format(manager.instance.__class__.__name__,
                                                                                 manager.field.related_query_name())

        def create_reverse_many_to_one_manager(*args, **kwargs):
            related_manager = original_create_reverse_many_to_one_manager(*args, **kwargs)

            self._patch_with_warnings(related_manager, "get_queryset", get_warning_message)

            return related_manager

        related_descriptors.create_reverse_many_to_one_manager = create_reverse_many_to_one_manager
