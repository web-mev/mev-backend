from .network_transforms import subset_PANDA_net
from .heatmap_transforms import heatmap_reduce

def get_transformation_function(transform_name):
    '''
    Re
    '''
    if transform_name == 'pandasubset':
        return subset_PANDA_net
    if transform_name == 'heatmap-reduce':
        return heatmap_reduce
    else:
        raise Exception('Could not find a transform keyed by {x}'.format(x=transform_name))