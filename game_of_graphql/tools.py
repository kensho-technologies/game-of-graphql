# Copyright 2017 Kensho Technologies, Inc.
"""Utilities for running the Game of GraphQL server."""
from time import sleep

from pyorient import PyOrientConnectionException
from pyorient.ogm import Config, Graph

from game_of_graphql import existing_dataset, new_dataset


def recreate_game_of_graphql_graph(orientdb_location, username, password):
    """If the Game of GraphQL graph isn't present, construct it from the GamesOfThrones one."""
    exising_config = Config.from_url(
        'plocal://{}/GamesOfThrones'.format(orientdb_location), username, password)
    new_config = Config.from_url(
        'plocal://{}/game_of_graphql'.format(orientdb_location), username, password)

    data = existing_dataset.load_all_data(exising_config)
    new_dataset.create_game_of_graphql_graph(new_config, data)


def wait_for_orientdb_to_come_alive(orientdb_location, username, password):
    """Block until OrientDB is ready to serve requests."""
    config = Config.from_url(
        'plocal://{}/GamesOfThrones'.format(orientdb_location), username, password)

    retries = 100

    for _ in range(retries):
        try:
            # This line will raise a connection error if OrientDB isn't ready yet.
            Graph(config, strict=True)
            return
        except PyOrientConnectionException:
            sleep(1.0)

    raise RuntimeError(u'Could not connect to OrientDB at {}. '
                       u'Giving up after {} retries.'.format(orientdb_location, retries))
