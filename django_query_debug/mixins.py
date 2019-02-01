from collections import defaultdict
import logging
import traceback

from django.db import models
from django.test import override_settings

from django_query_debug.utils import analyze_queryset, print_green, print_yellow

logger = logging.getLogger('query_analysis')


class QueryAnalysisModelMixin(object):
    """
    Model mixin that adds query analysis helper methods.

    To enable warnings for accessing unfetched related fields or
    to track model field usage, set the Django settings param
    ENABLE_QUERY_ANALYSIS to True.
    """

    def _print_traceback(self):
        """
        Print the traceback containing the method that triggered the query.

        Ignore the last 3 entries which would be the __getattribute__,
        warn_on_cold_cache, and the _print_traceback methods in this class.
        """
        stack = traceback.extract_stack(limit=18)[:-3]
        traceback.print_list(stack)

    def warn_on_cold_cache(self, item):
        """
        Print warnings when attempting to access a deferred field or an uncached related field.
        """
        _getattr = super(QueryAnalysisModelMixin, self).__getattribute__
        _meta = _getattr('_meta')

        try:
            field = _meta.get_field(item)
        except models.FieldDoesNotExist:
            # Ignore non-model fields
            return

        # A field is local if it is not a related field or if it is just the ID field for the related field
        is_local_field = field.related_model is None or (hasattr(field, 'get_attname') and field.get_attname() == item)
        is_m2m = field.many_to_many or field.one_to_many
        # Bottom of stack should be method x > __getattribute__ > warn_on_cold_cache
        is_prefetching = traceback.extract_stack(limit=3)[0][2] in ['prefetch_one_level', 'get_prefetcher']
        if hasattr(self, '_prefetched_objects_cache'):
            prefetched_objects = _getattr('_prefetched_objects_cache')
        else:
            prefetched_objects = {}
        deferred_fields = _getattr('get_deferred_fields')()
        class_name = _getattr('__class__')

        if is_local_field and item in deferred_fields:
            print_yellow("{0}: accessing deferred field `{1}`".format(class_name, item))
        elif is_m2m:
            prefetch_cache_name = getattr(_getattr(item), 'prefetch_cache_name', item)
            if not is_prefetching and prefetched_objects.get(prefetch_cache_name) is None:
                print_yellow("{0}: accessing non-prefetched m2m field `{1}`".format(class_name, item))
                logger.info('The following fields are prefetched: {}'.format(prefetched_objects.keys()))
                self._print_traceback()
        elif not is_local_field and not hasattr(self, field.get_cache_name()):
            print_yellow("{0}: accessing non-selected related field `{1}`".format(class_name, item))
            self._print_traceback()

        _getattr('track_field_usage')(item)

    def track_field_usage(self, field):
        """
        Track model field access/usage counts.
        """
        if not hasattr(self, '_field_usage'):
            initial_value = defaultdict(int, {
                model_field.name: 0
                for model_field in self._meta.get_fields()
            })
            initial_value[field] += 1
            setattr(self, '_field_usage', initial_value)
        else:
            usage = super(QueryAnalysisModelMixin, self).__getattribute__('_field_usage')
            usage[field] += 1

    @override_settings(ENABLE_QUERY_WARNINGS=False)
    def display_field_usage(self, indent_level=0, show_related=True):
        """
        Wrapper method around _display_field_usage to disable field tracking
        when displaying usage.
        """
        logger.info("Displaying field usage for `{}`:".format(self))
        self._display_field_usage(indent_level=indent_level, show_related=show_related)

    def _display_field_usage(self, indent_level=0, show_related=True):
        """
        Display field usage data.

        Will also display field usage data from related fields that also
        support field usage tracking.
        """
        if not hasattr(self, '_field_usage'):
            print_yellow("{}No field usage was tracked".format(' ' * indent_level))
            return

        for field_name, usage_count in self._field_usage.items():
            msg = '{}{}: {}'.format(' ' * indent_level, field_name, usage_count)

            if usage_count > 0:
                print_green(msg)
            else:
                logger.info(msg)

            field = self._meta.get_field(field_name)

            if not show_related or usage_count == 0 or field.related_model is None:
                continue
            if hasattr(field, 'get_attname') and field.get_attname() != field_name:
                continue
            if not hasattr(field.related_model, '_display_field_usage'):
                print_yellow("{}{} does not support field usage tracking".format(' ' * (indent_level + 2), field.related_model))
                continue

            # Display related field usage
            if hasattr(self, field.get_cache_name()):
                related_field = getattr(self, field.get_cache_name())
            else:
                related_field = getattr(self, field_name)

            if isinstance(related_field, models.Manager):
                for index, related_many_object in enumerate(related_field.all()):
                    logger.info('Object {}{}:'.format(' ' * (indent_level + 2), index))
                    related_many_object._display_field_usage(indent_level=indent_level + 4, show_related=show_related)
            elif isinstance(related_field, models.Model):
                related_field._display_field_usage(indent_level=indent_level + 2, show_related=show_related)

    # def __getattribute__(self, item):
    #     if getattr(settings, 'ENABLE_QUERY_ANALYSIS', False):
    #         super(QueryAnalysisModelMixin, self).__getattribute__('warn_on_cold_cache')(item)
    #
    #     return super(QueryAnalysisModelMixin, self).__getattribute__(item)

    class QuerySet(object):
        def analyze(self):
            analyze_queryset(self)
