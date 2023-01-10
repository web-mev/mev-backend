from .network_transforms import subset_PANDA_net
from .heatmap_transforms import heatmap_reduce
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
    else:
        raise Exception('Could not find a transform keyed'
                        f' by {transform_name}')