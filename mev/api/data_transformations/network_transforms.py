import pandas as pd
import numpy as np
import networkx as nx
from itertools import chain
from collections import defaultdict

from api.utilities.resource_utilities import check_resource_request_validity

from data_structures.attribute_types import PositiveIntegerAttribute

def subset_PANDA_net(resource_instance, query_params):
    '''

    Given a Resource (database row) and query params,
    returns a subset of top interacting feat/obs in matrix.

    `query_params` is a dict and has the following required keys:
    - maxdepth: how many levels deep to go 
    - children: how many children are investigated at each level (breadth)
    - axis: whether to start by looking at genes (0) or TFs (1)

    Additionally, one can start from a list of query genes to perform the subsequent
    walk down the network. That key is "initial_nodes"

    Returns:
        node_children_map (dict): Flattened map of nodes and children.
            keys = tuple of (node, axis)
            list = tuples of (child, edge weight)

    The input file is a gene-by-TF matrix. Each entry is a float
    '''

    MAX_NODES = 20

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
        init_nodes = [x.strip() for x in init_nodes.split(',')]
    except KeyError:
        # this is an optional parameter, so it's not a problem if it's not provided
        init_nodes = None

    # Import file as pandas dataframe
    df = pd.read_table(resource_instance.datafile.open(), header=0, index_col=0)

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

    if len(nodes) > MAX_NODES:
        raise Exception('Please choose fewer than {n} nodes to start. Networks with greater'
            ' numbers can be challenging to visualize.'.format(n=MAX_NODES)
        )

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


def subset_full_network(executed_op_instance, query_params):
    '''

    Given an ExecutedOperation instance (database row)
    and query params, returns a subset of top interacting feat/obs in matrix.

    Note that this network subsetting assumes the ExecutedOperation
    has TWO files -- 
    - a network file (i.e. a matrix). Examples include correlations, 
      partial correlations, etc. That is, entry (i,j) represents
      a measure of "connection" between nodes identified by i and j.
    - a "matched" matrix of significance values.

    The significance matrix allows us to filter the network to only
    the most significant entries, allowing users to prioritize 
    their investigation to the top candidates. 

    `query_params` is a dict and has the following required keys:
    - sig_threshold: the p-value/FDR/etc. which will be used as a threshold
      to subset the final matrix
    - scheme: this determines how we prioritize the network's info. See comments
             below
    - top_n: following prioritization of nodes or edges, this determines how
             many 'hits' we keep. Positive, non-zero integer
    - max_children: only relevant for the prioritization scheme where we rank
                    by "input weighting

    Additionally, one can start from a list of query genes to perform the subsequent
    walk down the network. That key is "initial_nodes"

    Returns:
        TODO
    '''
    # to keep this function as generic as possible, we need to know
    # which output keys from the executed operation contain the
    # relevant data. These should match keys in the outputs.
    try:
        weights_key = query_params['weights'].lower()
    except KeyError as ex:
        raise Exception(f'You must supply a "{ex}" parameter')

    try:
        pvals_key = query_params['pvals'].lower()
    except KeyError as ex:
        raise Exception(f'You must supply a "{ex}" parameter')

    
    # first determine the prioritization scheme.
    # - "max_edges": Finds the top edges in the graph. W can then obtain a
    #                node set corresponding to those `top_n` edges; call this
    #                the root node set. If `max_children` is provided, we then
    #                find the top `max_children` neighbors for each node in the
    #                root node set as given by the absolute value of the edge.
    #                If `max_children` is not provided, we only show the root
    #                node set and any edges connecting those nodes.
    # - "max_weight": Finds the nodes that have the maximum weighting. This is
    #                 given by the sum of the absolute values of the edges 
    #                 incident on each node. We then take the `top_n` of those.
    #                 Just as above, we have the ability to walk out to the 
    #                 to `max_children` nodes if the parameter is provided.
    # - "node_list": The user explicitly provides a set of root nodes to start
    #                from. Same as above with respect to `max_children` nodes.
    try:
        scheme = query_params['scheme'].lower()
    except KeyError as ex:
        raise Exception(f'You must supply a "{ex}" parameter')

    available_schemes = {
        'max_edges': max_edge_subsetting,
        'max_weight': max_weight_subsetting,
        'node_list': node_list_subsetting
    }
    if scheme in available_schemes.keys():
        subset_fn = available_schemes[scheme]
    else:
        raise Exception(f'"{scheme}" is not an available option. Please'
                        f' choose from {", ".join(available_schemes.keys())}')

    try:
        p = PositiveIntegerAttribute(int(query_params['max_children']))
        max_children = p.value
    except ValueError:
        raise Exception('The parameter "max_children" could not be parsed'
                        ' as a positive integer.')   
    except KeyError:
        # the `max_children` key is optional- set to zero.
        max_children = 0

    # note that below, we check for query params specific to the 
    # requested prioritization scheme. We handle the actual files
    # and function calls after. This way if there's an issue with
    # bad params, we return immediately rather than after a file
    # read, etc.
    if scheme == 'node_list':
        try:
            init_nodes = query_params['nodes'].lower()
        except KeyError as ex:
            raise Exception(f'Since the node ordering scheme requested expects'
                ' a list of nodes, you must supply a "{ex}" parameter')
    else:
        # we expect a parameter `top_n` in this case
        try:
            p = PositiveIntegerAttribute(int(query_params['top_n']))
            top_n = p.value
        except ValueError:
            raise Exception('The parameter "top_n" could not be parsed'
                            ' as a positive integer.')   
        except KeyError:
            raise Exception(f'Given the node ordering scheme requested,'
                ' you must supply a "{ex}" parameter')

    adj_mtx, pvals_mtx = get_result_matrices(executed_op_instance,
                                             weights_key,
                                             pvals_key)
    if scheme == 'node_list':
        G = subset_fn(adj_mtx, pvals_mtx, init_nodes, max_children)
    else:
        G = subset_fn(adj_mtx, pvals_mtx, top_n, max_children)

    output_json_dict = {}
    node_list = []
    for node, data in G.nodes.items():
        node_list.append({
            'id': node
        })
    output_json_dict['nodes'] = node_list
    edge_list = []
    for edge_tuple, edge_data in G.edges.items():
        edge_list.append({
            'source': edge_tuple[0],
            'target': edge_tuple[1],
            'weight': edge_data['weight'],
            'pval': edge_data['pval']
        })
    return output_json_dict


def get_result_matrices(executed_op_instance, weights_key, pvals_key):
    outputs = executed_op_instance.outputs
    try:
        weights_uuid = outputs[weights_key]
    except KeyError as ex:
        raise Exception(f'Could not locate key {ex} among job outputs.'
                        ' Please check your request.')
    try:
        pvals_uuid = outputs[pvals_key]
    except KeyError as ex:
        raise Exception(f'Could not locate key {ex} among job outputs.'
                        ' Please check your request.')

    weights_resource = check_resource_request_validity(
        executed_op_instance.owner, weights_uuid)

    pvals_resource = check_resource_request_validity(
        executed_op_instance.owner, pvals_uuid)

    weights_df = pd.read_table(weights_resource.datafile.open(), header=0, index_col=0)
    pvals_df = pd.read_table(pvals_resource.datafile.open(), header=0, index_col=0)

    return weights_df, pvals_df


def filter_by_significance(adj_mtx, pval_mtx, threshold):
    '''
    Filter the provided adjacency matrix to return a subnet
    that only contains nodes that have "significant" edges
    as determined by the `threshold` parameter.

    The returned dataframe still has np.nan entries for
    the "insignificant" entries. 
    '''
    m = adj_mtx.shape[0]
    pass_threshold = pval_mtx <= threshold
    pass_mtx = adj_mtx.where(pass_threshold)

    # fill the diagonal (which is supposed to be zero since
    # no self-connections) with NaN so we can easily 
    # drop rows/cols. This amounts to dropping nodes
    # that do not have any "significant" edges
    np.fill_diagonal(pass_mtx.values, np.nan)
    
    # sum the NAs in each row. If it equals the shape, we
    # can drop both the row and column (since symm mtx):
    is_all_nan = (pass_mtx.isna().sum(axis=0) == m)
    return pass_mtx.loc[~is_all_nan, ~is_all_nan]


def max_edge_subsetting(adj_mtx, pval_mtx, top_n, max_children):
    melted = adj_mtx.where(np.tril(np.ones_like(adj_mtx), k=-1).astype(bool))\
                     .melt(ignore_index=False)\
                     .dropna()\
                     .sort_values('value', ascending=False)\
                     .head(top_n)
    # melted looks like:
    #     variable     value
    # g2       g0  5.222781
    # m5       m1  4.530018
    # m5       m0  4.148508

    # create a graph of just the top edges
    G = nx.Graph()
    for i, row in melted.iterrows():
        j = row['variable']
        v = row['value']
        pval = pval_mtx.loc[i, j]
        G.add_edge(i, j, weight=v, pval=pval)

    if max_children > 0:
        root_nodes = [x[0] for x in G.nodes.data()]
        for node in root_nodes:
            row = adj_mtx.loc[node]
            pvals = pval_mtx.loc[node]
            G = get_top_children(G, row, pvals, node, max_children)
    return G


def get_top_children(G, row, pvals, i, n):

    if n == 0:
        return G

    # note that we get the top children using abs value
    row = row.dropna().abs().sort_values(ascending=False)[:n]
    for j, val in row.items():
        if i != j: # no self-link
            G.add_edge(i, j, weight=val, pval=pvals[j])
    return G


def max_weight_subsetting(adj_mtx, pval_mtx, top_n, max_children):

    # note the absolute value since we have correlation values--
    # we don't want cancellation of +/- in sum!
    row_sums = np.abs(adj_mtx).sum(axis=1)
    sorter = np.argsort(row_sums)[::-1][:top_n]
    adj_mtx = adj_mtx.iloc[sorter]
    adj_mtx = adj_mtx.dropna(axis=1, how='all')

    G = nx.Graph()
    
    if max_children > 0:
        # go row-by-row and get the top children
        for i, row in adj_mtx.iterrows():
            pvals = pval_mtx.loc[i]
            G = get_top_children(G, row, pvals, i, max_children)

    return G


def node_list_subsetting(adj_mtx, pval_mtx, root_node_list, max_children):
    diff_set = set(root_node_list).difference(adj_mtx.index)
    if len(diff_set) > 0:
        raise Exception(f'The following items were not found'
                        f' {", ".join(diff_set)}')

    adj_mtx = adj_mtx.loc[root_node_list, root_node_list]
    if max_children > 0:
        # go row-by-row and get the top children
        for i, row in adj_mtx.iterrows():
            pvals = pval_mtx.loc[i]
            G = get_top_children(G, row, pvals, i, max_children)

    return G
