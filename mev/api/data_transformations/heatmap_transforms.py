import logging

import numpy as np
from scipy.stats import median_abs_deviation
from scipy.cluster.hierarchy import dendrogram, linkage

from constants import MATRIX_KEY, \
    INTEGER_MATRIX_KEY, \
    EXPRESSION_MATRIX_KEY, \
    RNASEQ_COUNT_MATRIX_KEY
from api.utilities.resource_utilities import localize_resource
from api.data_structures import PositiveIntegerAttribute
from resource_types import get_resource_type_instance

logger = logging.getLogger(__name__)

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
        RNASEQ_COUNT_MATRIX_KEY
    ]
    if not resource.resource_type in acceptable_resource_types:
        raise Exception('Not an acceptable resource type for this function.')

    resource_type_instance = get_resource_type_instance(resource.resource_type)
    local_path = localize_resource(resource)
    resource_type_instance.read_resource(local_path, resource.file_format)
    df = resource_type_instance.table

    mad_values = median_abs_deviation(df, axis=1)
    sort_ordering = np.argsort(mad_values)[::-1][:mad_n]

    # use that sort order to subset the matrix:
    df = df.iloc[sort_ordering]

    '''
    See scipy for values. For metric, we have:
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
    return df.apply(resource_type_instance.main_contents_converter, axis=1).tolist()