import pandas as pd
from itertools import chain
from collections import defaultdict

from api.storage_backends import get_storage_backend
from api.data_structures import PositiveIntegerAttribute

def subset_PANDA_net(resource, query_params):
    '''

    Given a Resource (database row) and query params,
    perform the following:

    Returns a subset of top interacting feat/obs in matrix.
        Parameters:
            path_to_fname (str): Path to matrix file.
            max_depth (int): Max depth layers to traverse.
            N (int): Top N children to return.
            axis (int): Initial axis to start

        Returns:
            node_children_map (dict): Flattened map of nodes and children.
                keys = tuple of (node, axis)
                list = tuples of (child, edge weight)

    The input file is a gene-by-TF matrix. Each entry is a float
    '''

    def get_top_edges(df, nodes, axis, N):
        '''Sub-function for returning a single layer of sub-net.'''
        node_children_map = {}
        for node in nodes:
            largest_children = df.xs(node, axis).nlargest(N)
            node_children_map[(node, axis)] = dict(
                zip(
                    largest_children.index,
                    largest_children
                )
            )
        return node_children_map

    path_to_fname = get_storage_backend().get_local_resource_path(resource)

    try:
        p = PositiveIntegerAttribute(int(query_params['maxdepth']))
        max_depth = p.value
    except KeyError:
        raise Exception('You must supply a "maxdepth" parameter')
    except ValueError:
        raise Exception('The parameter "maxdepth" could not be parsed as an integer.')

    try:
        p = PositiveIntegerAttribute(int(query_params['children']))
        N = p.value
    except KeyError:
        raise Exception('You must supply a "children" parameter')
    except ValueError:
        raise Exception('The parameter "children" could not be parsed as an integer.')

    try:
        axis = int(query_params['axis'])
    except KeyError:
        raise Exception('You must supply a "axis" parameter')
    except ValueError:
        raise Exception('The parameter "axis" could not be parsed as an integer.')

    if not axis in [0,1]:
        raise Exception('The parameter "axis" must be 0 or 1.')

    # instead of providing the subset based on the top edge weights, we can start
    # from a user-supplied list of genes
    try:
        # a delimited string:
        init_nodes = query_params['initial_nodes']
        init_nodes = [x.strip() for x in init_nodes.split('///')]
    except KeyError:
        # this is an optional parameter, so it's not a problem if it's not provided
        init_nodes = None

    # Import file as pandas dataframe
    df = pd.read_table(path_to_fname, header=0, index_col=0)

    # Set initial variables
    initial_axis = axis
    current_level = 0
    node_children_map = defaultdict(dict)

    # First, establish initial nodes
    # Get the top N nodes as determined by the sum of the 
    # "attached" weights.
    summing_axis = int(not axis)

    if init_nodes is not None:
        if axis == 0:
            difference_set = set(init_nodes).difference(df.index)
        else:
            difference_set = set(init_nodes).difference(df.columns)
        if len(difference_set) > 0:
            msg = 'The following identifiers were not found in your {axis}: {id_list}'.format(
                axis= 'rows' if axis==0 else 'columns',
                id_list = ','.join(difference_set)
            )
            raise Exception(msg)
        # If we are here, then we are OK
        nodes = init_nodes
    else:
        nodes = df.sum(axis = summing_axis).nlargest(N).index

    # Find subsequent layers up to max_depth
    while current_level < max_depth:

        sub_map = get_top_edges(df, nodes, axis, N)

        # Traverse returned map and update node_children_map
        for k, v in sub_map.items():
            node_children_map[k].update(v)

        # A set of new nodes which 
        nodes = set(chain.from_iterable(sub_map.values()))

        axis = int(not axis) # hack to switch axis
        current_level += 1

    # Now to convert the above map into a JSON compatible dictionary
    # Initalize the JSON dict
    out_json_dict = {
        "initial_axis" : initial_axis,
        "nodes" : []
    }
    # Loops through all the root nodes
    for root, children in node_children_map.items():
        root_name, root_axis = root
        # Loops through all the Children to output an individual "dict"
        # for each child name and edge weight
        out_json_dict["nodes"].append(
            {
                root_name : {
                    "axis" : root_axis,
                    "children" : [
                        {k : v}
                        for k, v in children.items()
                    ]
                }
            }
        )
    return out_json_dict
