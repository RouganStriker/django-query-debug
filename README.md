![Build Status](https://travis-ci.org/RouganStriker/django-query-debug.svg?branch=master)
[![Coverage Status](https://coveralls.io/repos/github/RouganStriker/django-query-debug/badge.svg?branch=master)](https://coveralls.io/github/RouganStriker/django-query-debug?branch=master)

Helper methods and mixins for debugging query issues.

## Logging
All logs are sent to the `query_debug` logger.

## Django Settings:

| Setting | Default | Description |
|---------|---------|-------------|
| ENABLE_QUERY_WARNINGS | False | Enables warnings for access to unprefetched model fields. |
