# Copyright 2017 Kensho Technologies, Inc.
"""Create the GraphQL-compatible dataset from the existing dataset."""
from copy import deepcopy
from os import path
from uuid import uuid4

from pyorient.ogm import Graph
from pyorient.ogm.declarative import declarative_node, declarative_relationship


def _initialize_graph_connection(config, initial_drop=False):
    """Initialize a graph connection with the given configuration."""
    local_config = deepcopy(config)
    local_config.initial_drop = initial_drop

    graph = Graph(local_config, strict=True)
    base_node = declarative_node()
    base_relationship = declarative_relationship()
    graph.include(graph.build_mapping(base_node, base_relationship, auto_plural=True))
    return graph


def _apply_game_of_graphql_schema(client):
    """Apply the SQL commands necessary to create the Game of GraphQL schema."""
    schema_file = path.join(path.dirname(__file__), 'game_of_graphql.sql')

    with open(schema_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                client.command(line)


def _make_edges(graph_cls_broker, old_to_new_rid, rid_to_vertex, data):
    """Create all edges specified in the data on the given graph class broker."""
    for source_rid, destination_rid in data:
        if source_rid not in old_to_new_rid or destination_rid not in old_to_new_rid:
            continue

        source_rid = old_to_new_rid[source_rid]
        destination_rid = old_to_new_rid[destination_rid]

        graph_cls_broker.create(rid_to_vertex[source_rid], rid_to_vertex[destination_rid])


def create_game_of_graphql_graph(config, data):
    """Wipe out any data in the specified database and replace it with the Game of GraphQL graph."""
    graph = _initialize_graph_connection(config, initial_drop=True)
    _apply_game_of_graphql_schema(graph.client)

    # Creating the schema has invalidated the graph's object model, so we'll reload it.
    graph = _initialize_graph_connection(config, initial_drop=False)

    rid_to_vertex = {}
    old_to_new_rid = {}

    for character in data['characters'].values():
        vertex = graph.Character.create(
            name=character['name'], alias=character['alias'], uuid=str(uuid4()))
        old_to_new_rid[character['rid']] = vertex._id
        rid_to_vertex[vertex._id] = vertex

    for house in data['houses'].values():
        vertex = graph.NobleHouse.create(
            name=house['name'], alias=house['alias'], motto=house['motto'], uuid=str(uuid4()))
        old_to_new_rid[house['rid']] = vertex._id
        rid_to_vertex[vertex._id] = vertex

    for region in data['regions'].values():
        vertex = graph.Region.create(name=region['name'], alias=region['alias'], uuid=str(uuid4()))
        old_to_new_rid[region['rid']] = vertex._id
        rid_to_vertex[vertex._id] = vertex

    data_key_to_broker = {
        'has_seat': graph.Has_Seat,
        'has_parent_region': graph.Has_Parent_Region,
        'lives_in': graph.Lives_In,
        'owes_allegiance_to': graph.Owes_Allegiance_To,
    }

    for key, broker in data_key_to_broker.items():
        _make_edges(broker, old_to_new_rid, rid_to_vertex, data[key])

    return graph
