![Build Status](https://travis-ci.org/RouganStriker/django-query-debug.svg?branch=master)

Helper methods and mixins for debugging query issues.

## Logging
All logs are sent to the `query_debug` logger.

## Django Settings:

| Setting | Default | Description |
|---------|---------|-------------|
| ENABLE_QUERY_WARNINGS | False | Enables warnings for access to unprefetched model fields. |
