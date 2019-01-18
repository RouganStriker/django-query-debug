from contextlib import contextmanager
from functools import partial
import logging
import time

from django.db import connection, reset_queries
import sqlparse


class StringFormatter(object):
    formatters = {
        'GREEN': '\033[92m',
        'BLUE': '\033[94m',
        'RED': '\033[91m',
        'YELLOW': '\033[93m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'UNDERLINE': '\033[4m'
    }

    ENDC = '\033[0m'

    def format_me(self, msg, formatter):
        return formatter + msg + self.ENDC

    def __init__(self):
        # set formatter methods on the instance for all formatters
        # in StringFormatter.formatters
        # e.g. green(self, msg), blue(self, msg)
        for formatter, val in self.formatters.iteritems():
            method = partial(self.format_me, formatter=val)
            setattr(self, formatter.lower(), method)

logger = logging.getLogger('query_analysis')
formatter = StringFormatter()


def print_green(msg):
    logger.info(formatter.green(msg))


def print_yellow(msg):
    logger.warn(formatter.yellow(msg))


def format_sql(sql):
    """
    Format a SQL statement.

    If the pygments package is available, it will be used for syntax highlighting.
    """
    formatted_sql = sqlparse.format(sql, reindent=True, keyword_case='upper')

    try:
        import pygments
        from pygments.lexers import SqlLexer
        from pygments.formatters import TerminalTrueColorFormatter

        formatted_sql = pygments.highlight(
            formatted_sql,
            SqlLexer(),
            TerminalTrueColorFormatter(style='monokai')
        )
    except ImportError:
        pass

    return formatted_sql


@contextmanager
def analyze_block():
    """
    Context manager to analyze query usage of a block of code.

    Provides data on the following:
    * Time spent querying DB vs serializing results
    * Query counts and duplicate queries
    * Total rows fetched and serialized
    * Raw SQL statement, query time, and total rows fetched per query
    """
    reset_queries()
    start_time = time.time()

    yield

    elapsed_time = time.time() - start_time
    sql_queries = list(connection.queries)
    query_count = len(sql_queries)
    total_query_time = 0.0
    total_objects_fetched = 0
    duplicate_query_count = 0
    analyzed_queries = {}

    for index, query in enumerate(sql_queries):
        query_time = float(query['time'])
        total_query_time += float(query['time'])

        if query['sql'] in analyzed_queries:
            # Duplicate
            duplicate_query_count += 1
            analyzed_queries[query['sql']]['seen'] += 1
            # average out the time
            analyzed_queries[query['sql']]['time'] = (analyzed_queries[query['sql']]['time'] + query_time) / 2.0
        else:
            with connection.cursor() as cursor:
                cursor.execute(query['sql'])
                rows_fetched = len(cursor.fetchall())

            analyzed_queries[query['sql']] = {
                'time': query_time,
                'num_results': rows_fetched,
                'seen': 1,
            }

        total_objects_fetched += analyzed_queries[query['sql']]['num_results']
        total_query_time += float(query['time'])

    for index, (sql, analysis) in enumerate(analyzed_queries.items()):
        logger.info("Query {} summary".format(index))
        logger.info("-------------------------------")
        logger.info("SQL Statement")
        logger.info(format_sql(sql))
        logger.info("Query time: {}s".format(analysis['time']))
        logger.info("Number of results: {}".format(analysis['num_results']))
        if analysis['seen'] > 1:
            logger.info("Duplicated {} times".format(analysis['seen']))
        logger.info('\n')

    percent_query_time = round(total_query_time / elapsed_time * 100.0, 2)

    logger.info("Elapsed time: {}s".format(elapsed_time))
    logger.info("Time spent querying: {}s ({}%) ".format(total_query_time, percent_query_time))
    logger.info("Time spent serializing: {}s ({}%)".format(elapsed_time - total_query_time, 100.0 - percent_query_time))
    logger.info("Query count: {}".format(query_count))
    logger.info("Duplicate query count: {}".format(duplicate_query_count))
    logger.info("Total objects fetched: {}".format(total_objects_fetched))


def analyze_queryset(qs):
    """
    Analyze SQL query of queryset.
    """
    with analyze_block():
        evaluated_qs = list(qs)

    logger.info("Objects fetched by main queryset: {}".format(len(evaluated_qs)))
    logger.info("Main query explain: ")
    logger.info(qs.explain(analyze=True))
