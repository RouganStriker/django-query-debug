![Build Status](https://travis-ci.org/RouganStriker/django-query-debug.svg?branch=master)
[![Coverage Status](https://coveralls.io/repos/github/RouganStriker/django-query-debug/badge.svg?branch=master)](https://coveralls.io/github/RouganStriker/django-query-debug?branch=master)

A Django application containing helper methods and mixins for debugging query issues.

## Installation
Install package using `pip install django-query-debug`.

To use this package in an existing Django application, add `django_query_debug` to `INSTALLED_APPS` in your settings file. 

Example:
```python
INSTALLED_APPS = [
    'django_query_debug',
    ...
]
```

## Usage

### PatchDjangoDescriptors
Monkey patches the builtin Django field descriptors to log a warning message when a query call is about to be made. 
If the logging level is set to `DEBUG`, a stack trace will be logged to help find the line that is causing the query.

Sample usage:
```python
from django_query_debug.patch import PatchDjangoDescriptors

PatchDjangoDescriptors() 
```

### FieldUsageMixin
A model mixin that adds field usage tracking. Useful for determining which fields can be deferred during the 
initial DB query using `.only()` or `.exclude()`. 

To use, add the mixin to any model that extends from the Django `Model` class. 
It will wrap all model fields in that class with a custom descriptor that tracks access attempts.

Sample usage:
```python
from django.db import models

from django_query_debug.mixins import FieldUsageMixin

class MyModel(FieldUsageMixin, models.Model):
  name = models.CharField(max_length=255)
  related_model = models.ForeignKey(...)

```

Calling `display_field_usage()` on the model will log the output field usage data. 
Field usage data for any related model that inherits from `FieldUsageMixin` will also be displayed. 
To exclude data from related models, use `display_field_usage(show_related=False)`. 
To reset field usage data, call `reset_field_usage()` on that object.

Note: If a related object is referenced more than once via different fields, each occurrence will share 
the same field usage data because the underlying object is the same.

Sample output:
```bash
2019-03-03 15:02:41,727 [INFO] Displaying field usage for `MyModel object`:
2019-03-03 15:02:41,727 [INFO]   id: 5
2019-03-03 15:02:41,732 [INFO]   name: 1
2019-03-03 15:02:41,733 [INFO]   related_model: 1
2019-03-03 15:02:41,733 [INFO]     id: 1
2019-03-03 15:02:41,733 [INFO]     name: 1
2019-03-03 15:02:41,733 [INFO]   related_model_id: 1
```

If you are using custom metaclasses that inherit from the `ModelBase` class, you will need to 
combine your custom metaclass with the `django_query_debug.mixins.FieldUsageTrackerMeta` metaclass, 
and then extend the `FieldUsageMixin` mixin to use the new metaclass.

### analyze_queryset
Provides a SQL explaination of a given queryset. 
In Django 2.1+, this is a wrapper method around the `.explain()` method
of the queryset.

Sample usage:
```python
from django_query_debug.utils import analyze_queryset

analyze_queryset(Model.objets.all())
```

### analyze_block
A context manager that outputs debug information on all queries executed within that block of code. 
Outputs details such as the SQL statement, query time, number of results, 
number of query duplications, and the total time taken to execute the block of 
code divided between DB queries and everything else. 
The `DEBUG` setting must be set to True for Django to track queries.

Sample usage:
```python
from django_query_debug.utils import analyze_block

with analyze_block():
  list(Model.objets.all())
```

Sample output:
```bash
2019-03-03 15:38:10,739 [INFO] ------------------------------------------------------------
2019-03-03 15:38:10,740 [INFO] Query 0 summary
2019-03-03 15:38:11,014 [INFO] SQL Statement:
SELECT "mock_models_simplerelatedmodel"."id",
       "mock_models_simplerelatedmodel"."name",
       "mock_models_simplerelatedmodel"."related_model_id",
       "mock_models_simplerelatedmodel"."one_to_one_model_id"
FROM "mock_models_simplerelatedmodel"
WHERE "mock_models_simplerelatedmodel"."name" = 'Test 2'

2019-03-03 15:38:11,015 [INFO] Query time: 0.0s
2019-03-03 15:38:11,015 [INFO] Number of results: 1
2019-03-03 15:38:11,015 [INFO] ------------------------------------------------------------
2019-03-03 15:38:11,016 [INFO] Query 1 summary
2019-03-03 15:38:11,021 [INFO] SQL Statement:
SELECT "mock_models_simplerelatedmodel"."id",
       "mock_models_simplerelatedmodel"."name",
       "mock_models_simplerelatedmodel"."related_model_id",
       "mock_models_simplerelatedmodel"."one_to_one_model_id"
FROM "mock_models_simplerelatedmodel"

2019-03-03 15:38:11,021 [INFO] Query time: 0.0s
2019-03-03 15:38:11,022 [INFO] Number of results: 2
2019-03-03 15:38:11,022 [INFO] Duplicated 2 times
2019-03-03 15:38:11,022 [INFO] ------------------------------------------------------------
2019-03-03 15:38:11,022 [INFO] Query 2 summary
2019-03-03 15:38:11,028 [INFO] SQL Statement:
SELECT "mock_models_simplemodel"."id",
       "mock_models_simplemodel"."name"
FROM "mock_models_simplemodel"
WHERE "mock_models_simplemodel"."id" = 1

2019-03-03 15:38:11,029 [INFO] Query time: 0.0s
2019-03-03 15:38:11,029 [INFO] Number of results: 1
2019-03-03 15:38:11,029 [INFO] ============================================================
2019-03-03 15:38:11,029 [INFO] Elapsed time: 0.00437188148499s
2019-03-03 15:38:11,029 [INFO] Time spent querying: 0.0s (0.0%)
2019-03-03 15:38:11,030 [INFO] Time spent otherwise: 0.00437188148499s (100.0%)
2019-03-03 15:38:11,030 [INFO] Query count: 4
2019-03-03 15:38:11,030 [INFO] Duplicate query count: 1
2019-03-03 15:38:11,030 [INFO] Total objects fetched: 6
```

## Logging
All logs are sent to the `query_debug` logger. To enable stack traces with the query warnings, set the debug level to `DEBUG`.

Sample Configuration:

```python
LOGGING = {
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'query_debug': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    }
}
``` 

## Django Settings:

| Setting | Default | Description |
|---------|---------|-------------|
| ENABLE_QUERY_WARNINGS | False | Enable warnings for access to unprefetched model fields. |


## Development
After checking out repository, install using `python setup.py develop`.

To run tests, use `python setup.py test`.