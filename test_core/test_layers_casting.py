import numpy as np

from keras_core import ops
from keras_core import testing
from kgcnn.layers_core.casting import CastBatchedIndicesToDisjoint, CastBatchedAttributesToDisjoint


class CastBatchedGraphsToDisjointTest(testing.TestCase):

    nodes = np.array([[[0.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [1.0, 1.0]]])
    edges = np.array([[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [1.0, 1.0, 1.0]],
                      [[1.0, 0.0, 0.0], [1.0, 0.0, 1.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 1.0]]])
    edge_indices = np.array([[[0, 0], [0, 1], [1, 0], [1, 1]],
                             [[0, 0], [0, 1], [1, 0], [1, 1]]], dtype="int64")
    node_mask = np.array([[True, False], [True, True]])
    edge_mask = np.array([[True, False, False, False], [True, True, True, False]])
    node_len = np.array([1, 2], dtype="int64")
    edge_len = np.array([1, 3], dtype="int64")

    def test_correctness(self):

        layer = CastBatchedIndicesToDisjoint()
        layer_input = [self.nodes, ops.cast(self.edge_indices, dtype="int64"), self.node_len, self.edge_len]
        node_attr, edge_index, batch_node, batch_edge, node_id, edge_id, node_count, edge_count = layer(layer_input)
        self.assertAllClose(node_attr, [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
        self.assertAllClose(edge_index, [[0, 1, 2, 1], [0, 1, 1, 2]])
        self.assertAllClose(batch_node, [0, 1, 1])
        self.assertAllClose(batch_edge, [0, 1, 1, 1])
        self.assertAllClose(node_id, [0, 0, 1])
        self.assertAllClose(edge_id, [0, 0, 1, 2])
        self.assertAllClose(node_count, [1, 2])
        self.assertAllClose(edge_count, [1, 3])

        output_shape = layer.compute_output_shape([x.shape for x in layer_input])
        expected_output_shape = []

    def test_correctness_padding(self):

        layer = CastBatchedIndicesToDisjoint(padded_disjoint=True)
        layer_input = [self.nodes, ops.cast(self.edge_indices, dtype="int64"), self.node_len, self.edge_len]
        node_attr, edge_index, batch_node, batch_edge, node_id, edge_id, node_count, edge_count = layer(layer_input)

        self.assertAllClose(node_attr, [[0.0, 0.0], [0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
        self.assertAllClose(edge_index, [[0, 1, 0, 0, 0, 3, 4, 3, 0], [0, 1, 0, 0, 0, 3, 3, 4, 0]])
        self.assertAllClose(batch_node, [0, 1, 0, 2, 2])
        self.assertAllClose(batch_edge, [0, 1, 0, 0, 0, 2, 2, 2, 0])
        self.assertAllClose(node_id, [0, 0, 0, 0, 1])
        self.assertAllClose(edge_id, [0, 0, 0, 0, 0, 0, 1, 2, 0])
        self.assertAllClose(node_count, [1, 1, 2])
        self.assertAllClose(edge_count, [4, 1, 3])

        output_shape = layer.compute_output_shape([x.shape for x in layer_input])
        expected_output_shape = []


class TestCastBatchedGraphAttributesToDisjoint(testing.TestCase):

    nodes = np.array([[[0.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [1.0, 1.0]]])
    edges = np.array([[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [1.0, 1.0, 1.0]],
                      [[1.0, 0.0, 0.0], [1.0, 0.0, 1.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 1.0]]])
    edge_indices = np.array([[[0, 0], [0, 1], [1, 0], [1, 1]],
                             [[0, 0], [0, 1], [1, 0], [1, 1]]], dtype="int64")
    node_mask = np.array([[True, False], [True, True]])
    edge_mask = np.array([[True, False, False, False], [True, True, True, False]])
    node_len = np.array([1, 2], dtype="int64")
    edge_len = np.array([1, 3], dtype="int64")

    def test_correctness(self):

        layer = CastBatchedAttributesToDisjoint()
        node_attr, _, _ = layer([self.nodes, self.node_len])
        self.assertAllClose(node_attr, [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])

        # self.assertAllClose(edge_attr, [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 1.0], [1.0, 1.0, 0.0]])
        # self.assertAllClose(edge_attr, [[0.0, 0.0, 0.0],[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0],
        #     [1.0, 1.0, 1.0], [1.0, 0.0, 0.0], [1.0, 0.0, 1.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 1.0]])


if __name__ == "__main__":

    CastBatchedGraphsToDisjointTest().test_correctness()
    CastBatchedGraphsToDisjointTest().test_correctness_padding()
    TestCastBatchedGraphAttributesToDisjoint().test_correctness()
    print("Tests passed.")
