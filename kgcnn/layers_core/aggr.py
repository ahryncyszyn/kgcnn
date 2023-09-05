from keras_core.layers import Layer
from keras_core import ops


# @keras_core.saving.register_keras_serializable()
class Aggregate(Layer):

    def __init__(self, pooling_method: str = "sum", axis=0, **kwargs):
        super(Aggregate, self).__init__(**kwargs)
        self.pooling_method = pooling_method
        self.axis = axis
        if axis != 0:
            raise NotImplementedError
        
    def build(self, input_shape):
        super(Aggregate, self).build(input_shape)

    def compute_output_shape(self, input_shape):
        assert len(input_shape) == 3
        x_shape, _, dim_size = input_shape
        return tuple(list(dim_size) + list(x_shape[1:]))

    def call(self, inputs, **kwargs):
        x, index, dim_size = inputs
        # For test only sum scatter, no segment operation no other poolings etc.
        # will add all poolings here.
        shape = ops.concatenate([dim_size, ops.shape(x)[1:]])
        return ops.scatter(ops.expand_dims(index, axis=-1), x, shape=shape)


class AggregateLocalEdges(Layer):

    def __init__(self, pooling_method="scatter_sum", pooling_index: int = 1, **kwargs):
        super(AggregateLocalEdges, self).__init__(**kwargs)
        self.pooling_index = pooling_index
        self.to_aggregate = Aggregate(pooling_method=pooling_method)

    def build(self, input_shape):
        assert len(input_shape) == 3
        node_shape, edges_shape, edge_index_shape = input_shape
        self.to_aggregate.build((edges_shape, edge_index_shape[1:], node_shape[:1]))

    def compute_output_shape(self, input_shape):
        assert len(input_shape) == 3
        node_shape, edges_shape, edge_index_shape = input_shape
        return self.to_aggregate.compute_output_shape([edges_shape, edge_index_shape[1:], node_shape[:1]])

    def call(self, inputs, **kwargs):
        n, edges, edge_index = inputs
        return self.to_aggregate([edges, edge_index[self.pooling_index], ops.cast(ops.shape(n)[:1], dtype="int64")])


class AggregateWeightedLocalEdges(AggregateLocalEdges):

    def __init__(self, pooling_method="scatter_sum", pooling_index: int = 1, normalize_by_weights=False, **kwargs):
        super(AggregateWeightedLocalEdges, self).__init__(**kwargs)
        self.normalize_by_weights = normalize_by_weights
        self.pooling_index = pooling_index
        self.to_aggregate = Aggregate(pooling_method=pooling_method)
        self.to_aggregate_weights = Aggregate(pooling_method="scatter_sum")

    def build(self, input_shape):
        assert len(input_shape) == 4
        node_shape, edges_shape, edge_index_shape, weights_shape = input_shape
        self.to_aggregate.build((edges_shape, edge_index_shape[1:], node_shape[:1]))
        self.to_aggregate_weights.build((weights_shape, edge_index_shape[1:], node_shape[:1]))

    def compute_output_shape(self, input_shape):
        assert len(input_shape) == 4
        node_shape, edges_shape, edge_index_shape, weights_shape = input_shape
        return self.to_aggregate.compute_output_shape([edges_shape, edge_index_shape[1:], node_shape[:1]])

    def call(self, inputs, **kwargs):
        n, edges, edge_index, weights = inputs
        edges = edges*weights

        out = self.to_aggregate([edges, edge_index[self.pooling_index], ops.cast(ops.shape(n)[:1], dtype="int64")])

        if self.normalize_by_weights:
            norm = self.to_aggregate_weights([
                weights, edge_index[self.pooling_index], ops.cast(ops.shape(n)[:1], dtype="int64")])
            out = out/norm
        return out
