from ._model import model_disjoint
from kgcnn.models.utils import update_model_kwargs
from kgcnn.layers.scale import get as get_scaler
from kgcnn.layers.modules import Input
from keras_core.backend import backend as backend_to_use
from kgcnn.models.casting import template_cast_input, template_cast_output
from kgcnn.ops.activ import *

# Keep track of model version from commit date in literature.
# To be updated if model is changed in a significant way.
__model_version__ = "2023-10-30"

# Supported backends
__kgcnn_model_backend_supported__ = ["tensorflow", "torch", "jax"]
if backend_to_use() not in __kgcnn_model_backend_supported__:
    raise NotImplementedError("Backend '%s' for model 'GAT' is not supported." % backend_to_use())

# Implementation of GAT in `keras` from paper:
# Graph Attention Networks
# by Petar Veličković, Guillem Cucurull, Arantxa Casanova, Adriana Romero, Pietro Liò, Yoshua Bengio (2018)
# https://arxiv.org/abs/1710.10903


model_default = {
    "name": "GAT",
    "inputs": [
        {"shape": (None,), "name": "node_attributes", "dtype": "float32"},
        {"shape": (None,), "name": "edge_attributes", "dtype": "float32"},
        {"shape": (None, 2), "name": "edge_indices", "dtype": "int64"},
        {"shape": (), "name": "total_nodes", "dtype": "int64"},
        {"shape": (), "name": "total_edges", "dtype": "int64"}
    ],
    "input_tensor_type": "padded",
    "cast_disjoint_kwargs": {},
    "input_embedding": None,  # deprecated
    "input_node_embedding": {"input_dim": 95, "output_dim": 64},
    "input_edge_embedding": {"input_dim": 5, "output_dim": 64},
    "attention_args": {"units": 32, "use_final_activation": False, "use_edge_features": True,
                       "has_self_loops": True, "activation": "kgcnn>leaky_relu", "use_bias": True},
    "pooling_nodes_args": {"pooling_method": "scatter_mean"},
    "depth": 3, "attention_heads_num": 5,
    "attention_heads_concat": False,
    "verbose": 10,
    "output_embedding": "graph",
    "output_to_tensor": True,
    "output_tensor_type": "padded",
    "output_mlp": {"use_bias": [True, True, False], "units": [25, 10, 1],
                   "activation": ["relu", "relu", "sigmoid"]},
    "output_scaling": None,
}


@update_model_kwargs(model_default, update_recursive=0, deprecated=["input_embedding", "output_to_tensor"])
def make_model(inputs: list = None,
               input_tensor_type: str = None,
               cast_disjoint_kwargs: dict = None,
               input_embedding: dict = None,
               input_node_embedding: dict = None,
               input_edge_embedding: dict = None,
               attention_args: dict = None,
               pooling_nodes_args: dict = None,
               depth: int = None,
               attention_heads_num: int = None,
               attention_heads_concat: bool = None,
               name: str = None,
               verbose: int = None,
               output_embedding: str = None,
               output_to_tensor: bool = None,
               output_mlp: dict = None,
               output_scaling: dict = None,
               output_tensor_type: str = None,
               ):
    r"""Make `GAT <https://arxiv.org/abs/1710.10903>`_ graph network via functional API.
    Default parameters can be found in :obj:`kgcnn.literature.GAT.model_default`.

    Inputs:
        list: `[node_attributes, edge_attributes, edge_indices, total_nodes, total_edges]`

            - node_attributes (Tensor): Node attributes of shape `(batch, None, F)` or `(batch, None)`
              using an embedding layer.
            - edge_attributes (Tensor): Edge attributes of shape `(batch, None, F)` or `(batch, None)`
              using an embedding layer.
            - edge_indices (Tensor): Index list for edges of shape `(batch, None, 2)`.
            - total_nodes(Tensor): Number of Nodes in graph if not same sized graphs of shape `(batch, )` .
            - total_edges(Tensor): Number of Edges in graph if not same sized graphs of shape `(batch, )` .

    Outputs:
        Tensor: Graph embeddings of shape `(batch, L)` if :obj:`output_embedding="graph"`.

    Args:
        inputs (list): List of dictionaries unpacked in :obj:`tf.keras.layers.Input`. Order must match model definition.
        cast_disjoint_kwargs (dict): Dictionary of arguments for :obj:`CastBatchedIndicesToDisjoint` .
        input_tensor_type (str): Input type of graph tensor. Default is "padded".
        input_embedding (dict): Deprecated in favour of input_node_embedding etc.
        input_node_embedding (dict): Dictionary of arguments for nodes unpacked in :obj:`Embedding` layers.
        input_edge_embedding (dict): Dictionary of arguments for edge unpacked in :obj:`Embedding` layers.
        attention_args (dict): Dictionary of layer arguments unpacked in :obj:`AttentionHeadGAT` layer.
        pooling_nodes_args (dict): Dictionary of layer arguments unpacked in :obj:`PoolingNodes` layer.
        depth (int): Number of graph embedding units or depth of the network.
        attention_heads_num (int): Number of attention heads to use.
        attention_heads_concat (bool): Whether to concat attention heads, or simply average heads.
        name (str): Name of the model.
        verbose (int): Level of print output.
        output_embedding (str): Main embedding task for graph network. Either "node", "edge" or "graph".
        output_to_tensor (bool): Whether to cast model output to :obj:`tf.Tensor`.
        output_tensor_type (str): Output type of graph tensors such as nodes or edges. Default is "padded".
        output_mlp (dict): Dictionary of layer arguments unpacked in the final classification :obj:`MLP` layer block.
            Defines number of model outputs and activation.
        output_scaling (dict): Dictionary of layer arguments unpacked in scaling layers. Default is None.

    Returns:
        :obj:`ks.models.Model`
    """
    # Make input
    model_inputs = [Input(**x) for x in inputs]

    disjoint_model_inputs = template_cast_input(
        model_inputs, input_tensor_type=input_tensor_type, cast_disjoint_kwargs=cast_disjoint_kwargs)

    n, ed, disjoint_indices, batch_id_node, batch_id_edge, node_id, edge_id, count_nodes, count_edges = disjoint_model_inputs

    # Wrapping disjoint model.
    out = model_disjoint(
        [n, ed, disjoint_indices, batch_id_node, count_nodes],
        use_node_embedding=len(inputs[0]['shape']) < 2, use_edge_embedding=len(inputs[1]['shape']) < 2,
        input_node_embedding=input_node_embedding, input_edge_embedding=input_edge_embedding,
        attention_args=attention_args, pooling_nodes_args=pooling_nodes_args, depth=depth,
        attention_heads_num=attention_heads_num, attention_heads_concat=attention_heads_concat,
        output_embedding=output_embedding, output_mlp=output_mlp
    )

    # Output embedding choice
    out = template_cast_output(
        [out, batch_id_node, batch_id_edge, node_id, edge_id, count_nodes, count_edges],
        output_embedding=output_embedding, output_tensor_type=output_tensor_type,
        input_tensor_type=input_tensor_type, cast_disjoint_kwargs=cast_disjoint_kwargs,
    )

    if output_scaling is not None:
        scaler = get_scaler(output_scaling["name"])(**output_scaling)
        out = scaler(out)

    model = ks.models.Model(inputs=model_inputs, outputs=out, name=name)
    model.__kgcnn_model_version__ = __model_version__

    if output_scaling is not None:
        def set_scale(*args, **kwargs):
            scaler.set_scale(*args, **kwargs)

        setattr(model, "set_scale", set_scale)

    return model
