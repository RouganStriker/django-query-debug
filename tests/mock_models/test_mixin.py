from django.test import override_settings, TestCase
from testfixtures import LogCapture

from mock_models.models import (FieldTrackedSimpleModel,
                                FieldTrackedRelatedModel,
                                UntrackedSimpleModel)


@override_settings(ENABLE_QUERY_WARNINGS=False)
class TestFieldUsageTracker(TestCase):
    def setUp(self):
        super(TestFieldUsageTracker, self).setUp()

        self.test_model = FieldTrackedSimpleModel.objects.create(name="Test")
        self.untracked_model = UntrackedSimpleModel.objects.create(name="Untracked")
        self.test_related_model = FieldTrackedRelatedModel.objects.create(name="Test Related",
                                                                          related_model=self.test_model,
                                                                          one_to_one_model=self.test_model,
                                                                          untracked_model=self.untracked_model)
        self.test_related_model.many_models.add(self.test_model)

    def assertFieldUsageIncrease(self, model, attribute, field_usage_key=None):
        if field_usage_key is None:
            field_usage_key = attribute

        current_count = model.get_field_usage()[field_usage_key]

        getattr(model, attribute)

        self.assertEqual(model.get_field_usage()[field_usage_key], current_count + 1)

    def test_proxied_field_values_retrieval(self):
        """
        Test that the fields still return the correct values.
        """
        test_model = FieldTrackedSimpleModel.objects.get(name="Test")
        test_related_model = FieldTrackedRelatedModel.objects.get(name="Test Related")

        # Simple fields
        self.assertEqual(test_related_model.id, self.test_related_model.id)
        self.assertEqual(test_related_model.name, self.test_related_model.name)
        # Related fields
        self.assertEqual(test_related_model.related_model, test_model)
        self.assertEqual(test_related_model.one_to_one_model, test_model)
        # Many to many
        self.assertIn(test_model, test_related_model.many_models.all())
        # Reverse relations
        self.assertIn(test_related_model, test_model.reverse_related_model.all())
        self.assertEqual(test_related_model, test_model.reverse_one_to_one_model)
        self.assertIn(test_related_model, test_model.reverse_many_models.all())

    def test_proxied_field_values_modification(self):
        """
        Test that the fields can still be modified.
        """
        new_model = FieldTrackedSimpleModel.objects.create(name="New")
        test_related_model = FieldTrackedRelatedModel.objects.get(name="Test Related")
        test_related_model.name = "Test2"
        test_related_model.related_model = new_model
        test_related_model.one_to_one_model = new_model
        test_related_model.many_models.add(new_model)
        test_related_model.save()

        # Check current model is updated
        self.assertEqual(test_related_model.name, "Test2")
        self.assertEqual(test_related_model.related_model, new_model)
        self.assertEqual(test_related_model.one_to_one_model, new_model)
        self.assertIn(new_model, list(test_related_model.many_models.all()))

        model = FieldTrackedRelatedModel.objects.get(id=test_related_model.id)

        # Check retrieved model contains new values
        self.assertEqual(model.name, "Test2")
        self.assertEqual(model.related_model, new_model)
        self.assertEqual(model.one_to_one_model, new_model)
        self.assertIn(new_model, list(model.many_models.all()))

    def test_field_usage_tracker(self):
        test_model = FieldTrackedSimpleModel.objects.get(name="Test")
        test_related_model = FieldTrackedRelatedModel.objects.get(name="Test Related")

        self.assertFieldUsageIncrease(test_model, "id")
        self.assertFieldUsageIncrease(test_model, "name")
        self.assertFieldUsageIncrease(test_model, "reverse_one_to_one_model")
        self.assertFieldUsageIncrease(test_model, "reverse_many_models")
        self.assertFieldUsageIncrease(test_model, "reverse_related_model")

        self.assertFieldUsageIncrease(test_related_model, "id")
        self.assertFieldUsageIncrease(test_related_model, "name")
        self.assertFieldUsageIncrease(test_related_model, "related_model")
        self.assertFieldUsageIncrease(test_related_model, "related_model_id")
        self.assertFieldUsageIncrease(test_related_model, "one_to_one_model")
        self.assertFieldUsageIncrease(test_related_model, "one_to_one_model_id")
        self.assertFieldUsageIncrease(test_related_model, "many_models")

    def test_field_usage_reset(self):
        test_model = FieldTrackedSimpleModel.objects.get(name="Test")

        self.assertFieldUsageIncrease(test_model, "id")
        self.assertFieldUsageIncrease(test_model, "name")

        test_model.reset_field_usage()

        self.assertEqual(test_model.get_field_usage()["id"], 0)
        self.assertEqual(test_model.get_field_usage()["name"], 0)

    def test_field_usage_display(self):
        """Check that displayed field usage info is consistent."""
        test_related_model = FieldTrackedRelatedModel.objects.get(name="Test Related")
        test_related_model.reset_field_usage()

        # Trigger field usage
        self.assertEqual(test_related_model.id, self.test_related_model.id)
        self.assertEqual(test_related_model.name, self.test_related_model.name)
        self.assertEqual(test_related_model.related_model.name, self.test_model.name)
        self.assertEqual(test_related_model.one_to_one_model.name, self.test_model.name)
        self.assertEqual(test_related_model.untracked_model.name, self.untracked_model.name)
        self.assertEqual(len(test_related_model.many_models.all()), 1)
        self.assertEqual(test_related_model.related_model.reverse_one_to_one_model, test_related_model)

        with LogCapture("query_debug") as capture:
            test_related_model.display_field_usage()

        initial_logs = capture.actual()

        with LogCapture("query_debug") as capture:
            test_related_model.display_field_usage()

        capture.check(*initial_logs)
