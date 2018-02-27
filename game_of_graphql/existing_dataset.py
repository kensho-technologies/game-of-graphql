# Copyright 2017 Kensho Technologies, Inc.
"""Load the existing dataset into a form we can manipulate."""
import re
import string

from pyorient.ogm import Graph
from pyorient.ogm.declarative import declarative_node, declarative_relationship


def _initialize_graph_connection(config):
    """Initialize a graph connection with the given configuration."""
    graph = Graph(config, strict=True)
    base_node = declarative_node()
    base_relationship = declarative_relationship()
    graph.include(graph.build_mapping(base_node, base_relationship, auto_plural=True))
    return graph


def _load_vertices_from_query(graph, query):
    """Return all vertex data (keyed by @rid) from a given query."""
    return {
        x.oRecordData['rid'].get_hash(): x.oRecordData
        for x in graph.client.query(query, -1)
    }


def _split_up_multiple_entries(entry):
    """Split up lists of entries that have been recorded as a single string."""
    split_types = ['<br>', '<br/>', '<br />']
    for split_type in split_types:
        if split_type in entry:
            return entry.split(split_type)

    return [entry]


def _clean_up_string_entry(entry):
    """Remove leading and trailing whitespace and quote marks."""
    return entry.strip(string.whitespace + '"\'')


def _strip_potential_suffixes(entries, potential_suffixes):
    """Strip the potential suffixes from each entry in the given list."""
    result = []
    for entry in entries:
        for suffix in potential_suffixes:
            if entry.endswith(suffix):
                entry = entry[:-len(suffix)]

        if entry:
            result.append(entry)

    return result


_parenthesized_name_part = re.compile(r'\(.*\)')


def _strip_parenthesized_portions_of_names(name):
    """Remove parenthesized parts in names."""
    return _parenthesized_name_part.sub('', name)


def _load_characters(graph):
    """Load all character data."""
    characters = _load_vertices_from_query(
        graph, 'SELECT @rid AS rid, name, Aka FROM Character')

    alias_potential_suffixes = [
        '(formerly)',
        '(given name)',
        '(player-determined)',
    ]

    for character in characters.values():
        alias = []
        if 'Aka' in character:
            aka_items = character['Aka']
            del character['Aka']

            alias = _strip_potential_suffixes(
                (_clean_up_string_entry(x) for x in _split_up_multiple_entries(aka_items)),
                alias_potential_suffixes)

        character['alias'] = alias

        character['rid'] = character['rid'].get_hash()
        character['name'] = _clean_up_string_entry(
            _strip_parenthesized_portions_of_names(character['name']))

    return characters


def _load_houses(graph):
    """Load all noble house data."""
    raw_houses = _load_vertices_from_query(
        graph,
        'SELECT @rid AS rid, * FROM V WHERE @this INSTANCEOF "Noble_house" OR '
        '@this INSTANCEOF "Noblehouse"')
    potential_suffixes = [
        '(official)',
        '(common saying)',
    ]

    houses = dict()
    for key, raw_house in raw_houses.items():
        raw_name = raw_house['name']
        house_prefix = 'House '
        if raw_name.startswith(house_prefix):
            clean_name = _clean_up_string_entry(raw_name[len(house_prefix):])
            alias = [raw_name]
        else:
            clean_name = raw_name
            alias = [(house_prefix + clean_name)]

        house = {
            'name': clean_name,
            'alias': alias,
            'rid': raw_house['rid'].get_hash()
        }
        raw_motto = None
        if 'Words' in raw_house:
            raw_motto = raw_house['Words']
        elif 'Motto' in raw_house:
            raw_motto = raw_house['Motto']

        motto = []
        if raw_motto:
            temp_motto = _strip_potential_suffixes(
                (_clean_up_string_entry(x) for x in _split_up_multiple_entries(raw_motto)),
                potential_suffixes)
            motto = [_clean_up_string_entry(x) for x in temp_motto]
        house['motto'] = motto

        houses[key] = house

    return houses


WORLD_REGION_RID = 'region:world'
WESTEROS_REGION_RID = 'region:westeros'
ESSOS_REGION_RID = 'region:essos'


def _fill_in_missing_regions():
    """Produce region data for all regions not already in the source graph."""
    return {
        WORLD_REGION_RID: {
            'name': 'World',
            'alias': [],
            'rid': WORLD_REGION_RID,
        },
        WESTEROS_REGION_RID: {
            'name': 'Westeros',
            'alias': [],
            'rid': WESTEROS_REGION_RID,
        },
        ESSOS_REGION_RID: {
            'name': 'Essos',
            'alias': [],
            'rid': ESSOS_REGION_RID,
        }
    }


def _get_rid_for_name(entries, name):
    """Get the rid of the entry with the given name."""
    for entry in entries.values():
        if entry['name'] == name:
            return entry['rid']

    raise ValueError(u'No entry with name {} found in entries {}'.format(name, entries))


def _load_missing_region_edges(regions):
    """Fill in the missing Has_Parent_Region edges."""
    # Existing regions whose parent region is Westeros.
    westeros_children = [
        'Beyond the Wall',
        'The North',
        'Iron Islands',
        'The Riverlands',
        'The Vale of Arryn',
        'The Westerlands',
        'The Crownlands',
        'The Reach',
        'The Stormlands',
        'Dorne',
    ]
    westeros_children_rids = [
        _get_rid_for_name(regions, x)
        for x in westeros_children
    ]

    # Existing regions whose parent region is Essos.
    essos_children = [
        'Free Cities',
        'Red Waste',
        "Slaver's Bay",
        'Qarth',
        'Asshai',
        'Yi Ti',
        'Valyrian Peninsula',
        'Dothraki Sea',
        'Bayasabhad',
        'Samyrian',
    ]
    essos_children_rids = [
        _get_rid_for_name(regions, x)
        for x in essos_children
    ]

    # Existing regions whose parent region is World.
    world_children = [
        'Summer Islands',
        'Basilisk Isles',
        'Ibben',
        'Naath',
    ]
    world_children_rids = [
        _get_rid_for_name(regions, x)
        for x in world_children
    ] + [WESTEROS_REGION_RID, ESSOS_REGION_RID]

    existing_region_links = {
        'Beyond the Wall': [
            'North Grove',
            'Thenn',
        ],
        'The North': [
            'Cerwyn',
            'Winter town',
        ],
        'The Wall': [
            'The Nightfort',
            'Eastwatch-by-the-Sea',
        ],
        'The Gift': [
            'The Nightfort',
            'Eastwatch-by-the-Sea',
        ],
        'The Riverlands': [
            'Stone Mill',
            'Inn at the Crossroads',
            'Salt Rock',
        ],
        'The Reach': [
            'Long Table',
        ],
        'The Westerlands': [
            'The Banefort',
            'Ashemark',
        ],
        'The Vale of Arryn': [
            'Baelish Castle',
            'The Redfort',
        ],
        'Iron Islands': [
            'Hammerhorn',
        ],
        'The Stormlands': [
            'Estermont',
        ],
        'Dorne': [
            'Wyl',
            'Planky Town',
        ],
        "King's Landing": [
            "Littlefinger's brothel",
            'Dragonpit',
        ],
        'Oldtown': [
            'The Citadel',
        ],
        'Meereen': [
            "Daznak's Pit",
        ],
        'House of Black and White': [
            'Hall of Faces',
        ],
        'Dothraki Sea': [
            'Vaes Dothrak',
        ],
    }

    final_data = {
        WESTEROS_REGION_RID: westeros_children_rids,
        ESSOS_REGION_RID: essos_children_rids,
        WORLD_REGION_RID: world_children_rids,
    }

    result = []
    for parent_rid, child_rids in final_data.items():
        result.extend((x, parent_rid) for x in child_rids)

    for parent_name, children_names in existing_region_links.items():
        parent_rid = _get_rid_for_name(regions, parent_name)
        result.extend((_get_rid_for_name(regions, x), parent_rid) for x in children_names)

    return result


def _load_regions(graph):
    """Load all region data."""
    raw_regions = _load_vertices_from_query(
        graph,
        'SELECT @rid AS rid, name FROM V WHERE @this INSTANCEOF "Region" OR '
        '@this INSTANCEOF "Settlement"')

    regions = _fill_in_missing_regions()
    for key, raw_region in raw_regions.items():
        potential_suffixes = [
            '(region)',
            '(castle)',
            '(island)',
        ]
        clean_name = _clean_up_string_entry(
            _strip_potential_suffixes([raw_region['name']], potential_suffixes)[0])
        region = {
            'name': clean_name,
            'alias': [],
            'rid': key,
        }
        regions[key] = region

    return regions


def _load_vertex_data(graph):
    """Load and return all relevant vertices from the graph."""
    characters = _load_characters(graph)
    houses = _load_houses(graph)
    regions = _load_regions(graph)

    return characters, houses, regions


def _load_edges_from_query(graph, query):
    """Return edge data from the given query."""
    return [
        (x.oRecordData['out_rid'].get_hash(), x.oRecordData['in_rid'].get_hash())
        for x in graph.client.query(query, -1)
    ]


def _load_edge_data(graph, regions):
    """Load and return all relevant edges from the graph."""
    has_seat = _load_edges_from_query(
        graph,
        'SELECT inV().@rid AS in_rid, outV().@rid AS out_rid FROM Has_Seat')

    # The edges in the existing dataset point from parent to child region / settlement.
    # In the desired dataset, we want the edge to be the other way, so we switch
    # the "in_rid" and "out_rid" names.
    has_parent_region = _load_edges_from_query(
        graph, '''
        SELECT inV().@rid AS out_rid, outV().@rid AS in_rid FROM E WHERE
            (
                @this INSTANCEOF "Has_Castles" OR
                @this INSTANCEOF "Has_Cities" OR
                @this INSTANCEOF "Has_Towns" OR
                @this INSTANCEOF "Has_Villages" OR
                @this INSTANCEOF "Has_Regional+capital" OR
                @this INSTANCEOF "Has_Places"
            ) AND (
                inV() INSTANCEOF "Region" OR inV() INSTANCEOF "Settlement"
            ) AND (
                outV() INSTANCEOF "Region" OR outV() INSTANCEOF "Settlement"
            )
        ''') + _load_missing_region_edges(regions)

    lives_in = _load_edges_from_query(
        graph, '''
        SELECT inV().@rid AS in_rid, outV().@rid AS out_rid FROM Has_Place WHERE (
            (inV() INSTANCEOF "Region" OR inV() INSTANCEOF "Settlement") AND
            outV() INSTANCEOF "Character"
        )''')

    owes_allegiance_to = _load_edges_from_query(
        graph, '''
        SELECT inV().@rid AS in_rid, outV().@rid AS out_rid FROM Has_Allegiance WHERE (
            (
                inV() INSTANCEOF "Character" OR
                inV() INSTANCEOF "Noblehouse" OR
                inV() INSTANCEOF "Noble_house"
            ) AND (
                outV() INSTANCEOF "Character" OR
                outV() INSTANCEOF "Noblehouse" OR
                outV() INSTANCEOF "Noble_house"
            )
        )''')

    return set(has_seat), set(has_parent_region), set(lives_in), set(owes_allegiance_to)


def load_all_data(config):
    """Given OrientDB config pointing to the GamesOfThrones database, return a dict of all data."""
    graph = _initialize_graph_connection(config)
    characters, houses, regions = _load_vertex_data(graph)
    has_seat, has_parent_region, lives_in, owes_allegiance_to = _load_edge_data(graph, regions)

    return {
        'characters': characters,
        'houses': houses,
        'regions': regions,
        'has_seat': has_seat,
        'has_parent_region': has_parent_region,
        'lives_in': lives_in,
        'owes_allegiance_to': owes_allegiance_to,
    }
