from contextlib import contextmanager

from django.db.models import Prefetch
from django.test import override_settings, TestCase
from testfixtures import LogCapture

from mock_models.models import ChildSimpleModel, SimpleModel, SimpleRelatedModel


@override_settings(DEBUG=True, ENABLE_QUERY_WARNINGS=True)
class TestPatchedDescriptors(TestCase):
    """
    Test that query warnings are logged with setting enabled.

    With ENABLE_QUERY_WARNINGS = True, the patch should get automatically applied in apps.py.
    """

    def setUp(self):
        self.simple_model = SimpleModel.objects.create(name="Test")
        self.simple_model_2 = SimpleModel.objects.create(name="Test Many")
        self.simple_related_model = SimpleRelatedModel.objects.create(name="Test Related",
                                                                      related_model=self.simple_model,
                                                                      one_to_one_model=self.simple_model)
        self.simple_related_model.many_models.add(self.simple_model)
        self.simple_related_model.many_models.add(self.simple_model_2)

    @contextmanager
    def assertNumQueriesAndLogs(self, expected_queries, expected_logs=None):
        with self.assertNumQueries(expected_queries), LogCapture() as log_capture:
            yield

        if expected_logs is None:
            expected_logs = []

        log_capture.check(*[
            ('query_debug', 'WARNING', log) for log in expected_logs
        ])

    def test_settings_disable_logs(self):
        test_model = SimpleRelatedModel.objects.get(name="Test Related")
        expected_logs = ['Accessing uncached ManyToMany field SimpleRelatedModel.many_models']

        with override_settings(ENABLE_QUERY_WARNINGS=False), self.assertNumQueriesAndLogs(1):
            self.assertEqual(len(test_model.many_models.all()), 2)

        with override_settings(ENABLE_QUERY_WARNINGS=True), self.assertNumQueriesAndLogs(1, expected_logs):
            self.assertEqual(len(test_model.many_models.all()), 2)

    def test_refresh_from_db_calls(self):
        test_model = SimpleModel.objects.get(name="Test")

        with self.assertNumQueriesAndLogs(2):
            # Don't log for explicit calls to refresh all fields
            test_model.refresh_from_db()
            # Don't log when refreshing non-deferred fields
            test_model.refresh_from_db(fields=["name"])

    def test_changing_related_field(self):
        with self.assertNumQueriesAndLogs(0):
            self.simple_related_model.related_model = self.simple_model_2

            # Accessing new related field should not trigger warning because it is fetched already
            self.assertEqual(self.simple_related_model.related_model.name, self.simple_model_2.name)

        new_model = SimpleModel.objects.create(name="Test New")
        test_model = SimpleRelatedModel.objects.get(name="Test Related")
        expected_logs = ['Accessing uncached ManyToOne field SimpleRelatedModel.related_model']

        with self.assertNumQueriesAndLogs(1, expected_logs):
            test_model.related_model_id = new_model.id

            # Only the ID of the related field was change, the full object needs to be fetched
            self.assertEqual(test_model.related_model.name, new_model.name)

    def test_deferred_field(self):
        test_model = SimpleModel.objects.filter(name="Test").only('id').first()
        expected_logs = ['Accessing deferred field(s) name']

        # Initial access triggers query and log message
        with self.assertNumQueriesAndLogs(1, expected_logs):
            self.assertEqual(test_model.name, "Test")

        # No query or logs on subsequent access
        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(test_model.name, "Test")

    def test_foreign_key_field_forward_access_without_prefetch(self):
        related_model = SimpleRelatedModel.objects.get(name="Test Related")
        expected_logs = ['Accessing uncached ManyToOne field SimpleRelatedModel.related_model']

        # Test no query for accessing the _id field
        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(related_model.related_model_id, self.simple_model.id)

        # Initial access triggers query
        with self.assertNumQueriesAndLogs(1, expected_logs):
            self.assertEqual(related_model.related_model.name, self.simple_model.name)

        # Subsequent access should use cached value
        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(related_model.related_model.name, self.simple_model.name)

    def test_foreign_key_field_forward_access_with_prefetch(self):
        prefetched_related_model = (SimpleRelatedModel.objects.select_related('related_model')
                                                              .get(name="Test Related"))

        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(prefetched_related_model.related_model.name, "Test")

    def test_foreign_key_field_reverse_access_without_prefetch(self):
        simple_model = SimpleModel.objects.get(name="Test")
        expected_logs = ['Accessing uncached reverse ManyToOne field SimpleModel.reverse_related_model']

        with self.assertNumQueriesAndLogs(1, expected_logs):
            self.assertIn(self.simple_related_model, simple_model.reverse_related_model.all())

    def test_foreign_key_field_reverse_access_with_prefetch(self):
        prefetched_simple_model = (SimpleModel.objects.prefetch_related('reverse_related_model')
                                                      .get(name="Test"))

        with self.assertNumQueriesAndLogs(0):
            self.assertIn(self.simple_related_model, prefetched_simple_model.reverse_related_model.all())

    def test_one_to_one_parent_linked_field(self):
        parent_model = SimpleModel.objects.create(name="Parent")
        ChildSimpleModel.objects.create(name="Child Override", parent=parent_model)
        child_model = ChildSimpleModel.objects.get(name="Child Override")

        # Test no queries accessing parent linked field
        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(child_model.name, "Child Override")
            self.assertEqual(child_model.parent.name, "Child Override")

    def test_one_to_one_field_forward_access_without_prefetch(self):
        related_model = SimpleRelatedModel.objects.get(name=self.simple_related_model.name)
        expected_logs = ['Accessing uncached OneToOne field SimpleRelatedModel.one_to_one_model']

        # Test no query for accessing the foreign key id
        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(related_model.one_to_one_model_id, self.simple_model.id)

        # Initial access triggers query and log message
        with self.assertNumQueriesAndLogs(1, expected_logs):
            self.assertEqual(related_model.one_to_one_model.name, self.simple_model.name)

        # Subsequent access should not trigger another query
        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(related_model.one_to_one_model.name, self.simple_model.name)

    def test_one_to_one_field_forward_access_with_prefetch(self):
        prefetched_related_model = (SimpleRelatedModel.objects.select_related('one_to_one_model')
                                                              .get(name=self.simple_related_model.name))

        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(prefetched_related_model.one_to_one_model.name, self.simple_model.name)

    def test_one_to_one_field_reverse_access_without_prefetch(self):
        simple_model = SimpleModel.objects.get(name=self.simple_model.name)
        expected_logs = ['Accessing uncached reverse OneToOne field SimpleModel.reverse_one_to_one_model']

        # Initial access triggers query and log message
        with self.assertNumQueriesAndLogs(1, expected_logs):
            self.assertEqual(self.simple_related_model, simple_model.reverse_one_to_one_model)

        # Subsequent access should not trigger another query
        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(self.simple_related_model, simple_model.reverse_one_to_one_model)

    def test_one_to_one_field_reverse_access_with_prefetch(self):
        prefetched_simple_model = (SimpleModel.objects.prefetch_related('reverse_one_to_one_model')
                                                      .get(name=self.simple_model.name))

        with self.assertNumQueriesAndLogs(0):
            self.assertEqual(self.simple_related_model, prefetched_simple_model.reverse_one_to_one_model)

    def test_many_to_many_field_access_without_prefetch(self):
        test_model = SimpleRelatedModel.objects.get(name="Test Related")
        expected_logs = ['Accessing uncached ManyToMany field SimpleRelatedModel.many_models']

        with self.assertNumQueriesAndLogs(1, expected_logs):
            models = list(test_model.many_models.all())
            self.assertEqual(models, [self.simple_model, self.simple_model_2])

    def test_many_to_many_field_access_with_prefetch(self):
        test_model = SimpleRelatedModel.objects.prefetch_related('many_models').get(name="Test Related")
        custom_prefetch = Prefetch('many_models', SimpleModel.objects.all(), 'prefetched_many_models')
        test_model_with_custom_prefetch = (SimpleRelatedModel.objects.prefetch_related(custom_prefetch)
                                                                     .get(name="Test Related"))
        expected_logs = ['Accessing uncached ManyToMany field SimpleRelatedModel.many_models']

        with self.assertNumQueriesAndLogs(0):
            models = list(test_model.many_models.all())
            custom_prefetched_models = test_model_with_custom_prefetch.prefetched_many_models

            self.assertEqual(models, [self.simple_model, self.simple_model_2])
            self.assertEqual(custom_prefetched_models, [self.simple_model, self.simple_model_2])

        # Accessing the non-prefetched attribute will trigger warning
        with self.assertNumQueriesAndLogs(1, expected_logs):
            models = list(test_model_with_custom_prefetch.many_models.all())
            self.assertEqual(models, [self.simple_model, self.simple_model_2])

    def test_reverse_many_to_many_field_access_without_prefetch(self):
        test_model = SimpleModel.objects.get(name="Test")
        expected_logs = ['Accessing uncached ManyToMany field SimpleModel.reverse_many_models']

        with self.assertNumQueriesAndLogs(1, expected_logs):
            models = list(test_model.reverse_many_models.all())
            self.assertEqual(models, [self.simple_related_model])

    def test_reverse_many_to_many_field_access_with_prefetch(self):
        test_model = SimpleModel.objects.prefetch_related("reverse_many_models").get(name="Test")
        custom_prefetch = Prefetch('reverse_many_models', SimpleRelatedModel.objects.all(), 'prefetched_many_models')
        test_model_with_custom_prefetch = (SimpleModel.objects.prefetch_related(custom_prefetch)
                                                              .get(name="Test"))
        expected_logs = ['Accessing uncached ManyToMany field SimpleModel.reverse_many_models']

        with self.assertNumQueriesAndLogs(0):
            models = list(test_model.reverse_many_models.all())
            custom_prefetched_models = test_model_with_custom_prefetch.prefetched_many_models

            self.assertEqual(models, [self.simple_related_model])
            self.assertEqual(custom_prefetched_models, [self.simple_related_model])

        # Accessing the non-prefetched attribute will trigger warning
        with self.assertNumQueriesAndLogs(1, expected_logs):
            models = list(test_model_with_custom_prefetch.reverse_many_models.all())
            self.assertEqual(models, [self.simple_related_model])
