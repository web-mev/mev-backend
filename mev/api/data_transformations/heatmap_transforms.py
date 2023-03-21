import logging

import numpy as np
from scipy.stats import median_abs_deviation
from scipy.cluster.hierarchy import dendrogram, linkage

from constants import MATRIX_KEY, \
    INTEGER_MATRIX_KEY, \
    EXPRESSION_MATRIX_KEY, \
    RNASEQ_COUNT_MATRIX_KEY, \
    FEATURE_TABLE_KEY
from data_structures.attribute_types import PositiveIntegerAttribute

from resource_types import get_resource_type_instance, get_contents

logger = logging.getLogger(__name__)


def perform_clustering(df, method, metric, resource_type_instance):
    '''
    See scipy reference for args. For metric, we have:
    ‘braycurtis’, ‘canberra’, ‘chebyshev’, ‘cityblock’, ‘correlation’, ‘cosine’, ‘dice’, ‘euclidean’, ‘hamming’, ‘jaccard’, ‘jensenshannon’, ‘kulczynski1’, ‘mahalanobis’, ‘matching’, ‘minkowski’, ‘rogerstanimoto’, ‘russellrao’, ‘seuclidean’, ‘sokalmichener’, ‘sokalsneath’, ‘sqeuclidean’, ‘yule’
    For method, we have:
    'single','complete', 'average', 'centroid','median', 'ward', 'weighted'
    
    Note that some methods require particular metrics (e.g. ward requires euclidean).
    Rather than worry about that, we just generically catch exceptions raised by
    the linkage method

    Recall that scipy operates transposed to how we consider matrices. That is, 
    in the scipy world, ROWS of a matrix are observations. Our convention (based
    on expression matrices) is to have observations in columns.
    '''
    try:
        row_linkage = linkage(df, method=method, metric=metric)
        col_linkage = linkage(df.T, method=method, metric=metric)
    except ValueError as ex:
        logger.info('Failed to create linkage. Reason was: {x}'.format(x=ex))
        raise Exception(str(ex))

    row_dendrogram = dendrogram(
        row_linkage,
        no_plot=True
    )
    col_dendrogram = dendrogram(
        col_linkage,
        no_plot=True
    )

    # the `leaves` key has the ordering as read from
    # left-to-right (or top to bottom).
    row_order = df.index[row_dendrogram['leaves']]    
    col_order = df.columns[col_dendrogram['leaves']]

    # reorder the matrix to correspond to the clustering
    df = df.loc[row_order, col_order]
    # convert to our usual return payload
    return resource_type_instance.to_json(df)


def heatmap_reduce(resource, query_params):
    '''
    This function finds the top N rows by median absolute deviation (MAD)
    and then performing a hierarchical clustering on that.

    The resource is expected to have a Matrix (MTX) resource type:
    tf    sampleA       sampleB       sampleC ...
    tA     0.2           0.3           0.5
    tB     0.21          0.1           0.55
    '''

    try:
        p = PositiveIntegerAttribute(int(query_params['mad_n']))
        mad_n = p.value
    except KeyError:
        raise Exception('You must supply a "mad_n" parameter')
    except ValueError:
        raise Exception('The parameter "mad_n" could not be parsed as an integer.')

    try:
        metric = query_params['metric']
    except KeyError:
        metric = 'euclidean'

    try:
        method = query_params['method']
    except KeyError:
        method = 'ward'

    acceptable_resource_types = [
        MATRIX_KEY,
        EXPRESSION_MATRIX_KEY,
        INTEGER_MATRIX_KEY,
        RNASEQ_COUNT_MATRIX_KEY,
        FEATURE_TABLE_KEY
    ]
    if not resource.resource_type in acceptable_resource_types:
        raise Exception('Not an acceptable resource type for this function.')

    resource_type_instance = get_resource_type_instance(resource.resource_type)
    resource_type_instance.read_resource(resource, resource.file_format)
    df = resource_type_instance.table
    try:
        mad_values = median_abs_deviation(df, axis=1)
    except:
        raise Exception('Could not calculate the median absolute deviation when preparing'
            ' the heatmap data. Often this is due to non-numerical data in your table.'
            ' If you are using a feature table or other file that can contain'
            ' non-numerical entries, you cannot use this data transformation.')
    sort_ordering = np.argsort(mad_values)[::-1][:mad_n]

    # use that sort order to subset the matrix:
    df = df.iloc[sort_ordering]

    return perform_clustering(df, method, metric, resource_type_instance)


def heatmap_cluster(resource, query_params):

    # note that we pop the transform-specific keys so we can submit
    # the remaining filters to the "general" dataframe filtering
    try:
        metric = query_params.pop('metric')
    except KeyError:
        metric = 'euclidean'

    try:
        method = query_params.pop('method')
    except KeyError:
        method = 'ward'

    acceptable_resource_types = [
        MATRIX_KEY,
        EXPRESSION_MATRIX_KEY,
        INTEGER_MATRIX_KEY,
        RNASEQ_COUNT_MATRIX_KEY,
        FEATURE_TABLE_KEY
    ]
    if not resource.resource_type in acceptable_resource_types:
        raise Exception('Not an acceptable resource type for this function.')

    resource_type_instance = get_resource_type_instance(resource.resource_type)
    # Note that the following method returns a json-format data structure
    # since it's typically used by a view. However, we use it to populate
    # an attribute on the instance which has the underlying dataframe
    get_resource_type_instance.get_contents(resource, query_params)
    df = resource_type_instance.table
    return perform_clustering(df, method, metric, resource_type_instance)
