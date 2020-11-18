class SimpleDag(object):

    def __init__(self):
        self.nodes = set()

    def add_node(self, node):
        if type(node) is DagNode:
            self.nodes.add(node)
        else:
            raise Exception('Can only add nodes to this DAG.')

    def serialize(self):
        return [x.serialize() for x in self.nodes]

    def __contains__(self, node):
        '''
        Overload so we can write something like "if node in graph"...
        '''
        return node in self.nodes

class DagNode(object):
    
    OP_NODE = 'op_node'
    DATARESOURCE_NODE = 'data_resource_node'

    NODE_TYPES = [OP_NODE, DATARESOURCE_NODE]

    def __init__(self, node_id, node_type, node_name = ''):
        if not node_type in DagNode.NODE_TYPES:
            raise Exception('Invalid node type. Choose from: {s}'.format(
            s = ', '.join(DagNode.NODE_TYPES)
        ))
        self.node_id = node_id
        self.node_type = node_type
        self.node_name = node_name
        self.parents = set()
        #TODO add other info

    def add_parent(self, new_parent):
        if type(new_parent) is DagNode:
            self.parents.add(new_parent)
        else:
            raise Exception('Can only add a parent of the correct type.')

    def serialize(self):
        node_info = {}
        node_info['id'] = self.node_id
        node_info['node_type'] = self.node_type
        node_info['node_name'] = self.node_name
        node_info['parentIds'] = [x.node_id for x in self.parents]
        return node_info

    def __eq__(self, other):
        '''
        Element equality is determined solely by the identifier field.
        '''
        x1 = self.node_id == other.node_id
        x2 = self.node_type == other.node_type
        return all([x1,x2])

    def __hash__(self):
        '''
        We implement a hash method so we can use set operations if necessary
        '''
        x = '{x1}-{x2}'.format(
            x1 = self.node_id,
            x2 = self.node_type
        )
        return hash(x)
