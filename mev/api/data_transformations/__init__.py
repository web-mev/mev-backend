from .network_transforms import subset_PANDA_net, \
    subset_full_network
from .heatmap_transforms import heatmap_reduce, heatmap_cluster
from .volcano_plot_transforms import volcano_subset


def get_transformation_function(transform_name):
    '''
    Returns a function that performs the desired transformation
    of the data contained in a file/resource
    '''
    if transform_name == 'pandasubset':
        return subset_PANDA_net
    if transform_name == 'heatmap-reduce':
        return heatmap_reduce
    if transform_name == 'volcano-subset':
        return volcano_subset
    if transform_name == 'heatmap-cluster':
        return heatmap_cluster
    if transform_name == 'networksubset':
        return subset_full_network
    else:
        raise Exception('Could not find a transform keyed'
                        f' by {transform_name}')