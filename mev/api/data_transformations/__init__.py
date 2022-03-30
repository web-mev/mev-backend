from .network_transforms import subset_PANDA_net

def get_transformation_function(transform_name):
    '''
    Re
    '''
    if transform_name == 'pandasubset':
        return subset_PANDA_net
    else:
        raise Exception('Could not find a transform keyed by {x}'.format(x=transform_name))