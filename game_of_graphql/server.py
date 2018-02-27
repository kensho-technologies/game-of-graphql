# Copyright 2017 Kensho Technologies, Inc.
"""Server that can compile and execute GraphQL queries."""
import json
from os import path

import click
from flask import Flask, abort, request
from flask_cors import CORS, cross_origin
from graphql import parse
from graphql.type.definition import GraphQLType
from graphql.utils.build_ast_schema import build_ast_schema
from graphql_compiler import graphql_to_match, pretty_print_graphql
from graphql_compiler.debugging_utils import pretty_print_match
from pyorient import OrientDB
from pyorient.ogm import Config
import six

from game_of_graphql import tools


app = Flask('game_of_graphql')
CORS(app, send_wildcard=True)
graph_config = None


def _load_schema():
    """Load the GraphQL schema from the schema file."""
    with open(path.join(path.dirname(__file__), 'game_of_graphql.graphql')) as f:
        schema_text = ''.join(f.readlines())

    ast = parse(schema_text)
    return build_ast_schema(ast)


schema = _load_schema()


WELCOME_TEXT = '''Hello world!

Try sending a POST to the /graphql endpoint, with a JSON dict payload:
    query: a GraphQL query string to compile and execute
    args: a dict, argument name -> argument value, to insert into the query

Enjoy!
'''


@app.route('/', methods=['GET'])
def root():
    """Return the welcome text, explaining how to use the server."""
    return WELCOME_TEXT


@app.route('/graphql', methods=['POST'])
@cross_origin()
def graphql():
    """Sanitize the input, then execute the provided GraphQL query and return the result."""
    data = request.get_json(force=True)
    if not data:
        app.logger.error(u'No data received: %s', data)
        return abort(400)

    query = data.get('query', None)
    if not query or not isinstance(query, six.string_types):
        app.logger.error(u'No valid query data received: %s', query)
        return abort(400)

    args = data.get('args', None)
    if args is None or not isinstance(args, dict):  # empty dict args is valid
        app.logger.error(u'No valid args data received: %s', args)
        return abort(400)

    # pylint: disable=broad-except
    try:
        return json.dumps(_run_graphql_query(query, args), default=_graphql_type_json_encoder)
    except Exception as e:
        app.logger.error(u'Encountered an error: %s', e)
        return str(e), 500, []
    # pylint: enable=broad-except


def _graphql_type_json_encoder(obj):
    """Encode GraphQL type objects as strings for JSON encoding."""
    if isinstance(obj, GraphQLType):
        return six.text_type(obj)
    else:
        raise TypeError(u'Cannot encode this object: %s', obj)


def _get_orientdb_client():
    """Return a connection to the graph."""
    client = OrientDB(graph_config.host, graph_config.port, graph_config.serialization_type)
    client.connect(graph_config.user, graph_config.cred)
    client.db_open(graph_config.db_name, graph_config.user, graph_config.cred)
    return client


def _run_graphql_query(query, args):
    """Execute the provided GraphQL query and return the result."""
    client = None
    try:
        client = _get_orientdb_client()

        compilation_result = graphql_to_match(schema, query, args)
        pretty_printed = pretty_print_graphql(query)

        limit = 1000
        outputs = [
            x.oRecordData
            for x in client.command(compilation_result.query, limit)
        ]

        return {
            'supplied_graphql': pretty_printed,
            'supplied_args': args,
            'input_metadata': compilation_result.input_metadata,
            'output_metadata': {
                # Named tuples JSON-encode to lists. Make them a proper dict.
                key: {'type': value.type, 'optional': value.optional}
                for key, value in compilation_result.output_metadata.items()
            },
            'executed_match_query': pretty_print_match(compilation_result.query),
            'output_data': outputs,
        }
    finally:
        if client:
            client.close()


@click.command()
@click.option('--host', type=str, default='127.0.0.1',
              help='Serve at this ip')
@click.option('--port', type=int, default=5000,
              help='Port where to run the service')
@click.option('--graph-location', type=str, default='127.0.0.1:2424',
              help='OrientDB host and port')
@click.option('--graph-user', type=str, default='root',
              help='OrientDB username')
@click.option('--graph-password', type=str, default='root',
              help='OrientDB password')
def run(host, port, graph_location, graph_user, graph_password):
    """Run the app."""
    # pylint: disable=global-statement
    global graph_config
    # pylint: enable=global-statement
    graph_config = Config.from_url(
        'plocal://{}/game_of_graphql'.format(graph_location), graph_user, graph_password)

    app.logger.info(u'Waiting for OrientDB to come alive...')
    tools.wait_for_orientdb_to_come_alive(graph_location, graph_user, graph_password)

    app.logger.info(u'Recreating the Game of GraphQL graph...')
    tools.recreate_game_of_graphql_graph(graph_location, graph_user, graph_password)

    app.logger.info(u'Starting server...')
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    run()
