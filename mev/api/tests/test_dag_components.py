import unittest
import uuid

from api.data_structures import DagNode, SimpleDag

class NodeTester(unittest.TestCase):

    def test_equality(self):
        u1 = uuid.uuid4()
        n1 = DagNode(str(u1), DagNode.OP_NODE)
        n2 = DagNode(str(u1), DagNode.OP_NODE)
        self.assertEqual(n1, n2)    

        # since we are using UUIDs, we could just compare on those
        # However, we'll be extra careful and also check that the node
        # types are the same
        n1 = DagNode(str(u1), DagNode.OP_NODE)
        n2 = DagNode(str(u1), DagNode.DATARESOURCE_NODE)
        self.assertNotEqual(n1, n2) 

    def test_add_parent(self):
        '''
        Test that the serialized representation is as expected.
        '''
        u1 = uuid.uuid4()
        n1 = DagNode(str(u1), DagNode.OP_NODE)

        u2 = uuid.uuid4()
        n2 = DagNode(str(u2), DagNode.OP_NODE)

        u3 = uuid.uuid4()
        n3 = DagNode(str(u3), DagNode.DATARESOURCE_NODE)

        n1.add_parent(n2)
        n1.add_parent(n3)
        
        d = n1.serialize()
        self.assertCountEqual(d['parentIds'], [str(u2), str(u3)])

    def test_add_duplicate_parent(self):
        '''
        Test that when we add a parent node for a second time, no
        difference is made
        '''
        u1 = uuid.uuid4()
        n1 = DagNode(str(u1), DagNode.OP_NODE)

        u2 = uuid.uuid4()
        n2 = DagNode(str(u2), DagNode.OP_NODE)

        u3 = uuid.uuid4()
        n3 = DagNode(str(u3), DagNode.DATARESOURCE_NODE)

        n1.add_parent(n2)
        n1.add_parent(n3)
        n1.add_parent(n2)

        d = n1.serialize()
        self.assertCountEqual(d['parentIds'], [str(u2), str(u3)])

class GraphTester(unittest.TestCase):

    def test_graph_add_node(self):

        graph = SimpleDag()

        u1 = uuid.uuid4()
        n1 = DagNode(str(u1), DagNode.OP_NODE)

        u2 = uuid.uuid4()
        n2 = DagNode(str(u2), DagNode.OP_NODE)

        u3 = uuid.uuid4()
        n3 = DagNode(str(u3), DagNode.DATARESOURCE_NODE)

        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_node(n1)

        n1.add_parent(n2)
        n1.add_parent(n3)
        n2.add_parent(n3)

        self.assertTrue(len(graph.nodes), 3)

        # check the serialized representation
        serialized_graph = graph.serialize()
        mapping = {
            str(u1): 'n1',
            str(u2): 'n2',
            str(u3): 'n3'
        }
        node_mapping = {}
        for node in serialized_graph:
            node_mapping[mapping[node['id']]] = node['parentIds']

        self.assertCountEqual(node_mapping['n1'], [str(u2), str(u3)])
        self.assertCountEqual(node_mapping['n2'], [str(u3)])
        self.assertCountEqual(node_mapping['n3'], [])

