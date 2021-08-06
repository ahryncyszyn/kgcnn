import tensorflow as tf
import tensorflow.keras as ks
import pprint

from kgcnn.layers.conv.attention import AttentionHeadGATV2
from kgcnn.layers.casting import ChangeTensorType
from kgcnn.layers.keras import Concatenate, Dense, Average, Activation
from kgcnn.layers.mlp import MLP
from kgcnn.layers.pool.pooling import PoolingNodes
from kgcnn.utils.models import generate_node_embedding, update_model_kwargs_logic, generate_edge_embedding


# Graph Attention Networks by Veličković et al. (2018)
# https://arxiv.org/abs/1710.10903
# Improved by
# How Attentive are Graph Attention Networks?
# by Brody et al. (2021)

def make_model(**kwargs):
    """Generate Graph attention network.

    Args:
        **kwargs

    Returns:
        tf.keras.models.Model: GAT model.
    """
    model_args = kwargs
    model_default = {'name': "GATv2",
                     'inputs': [{'shape': (None,), 'name': "node_attributes", 'dtype': 'float32', 'ragged': True},
                                {'shape': (None,), 'name': "edge_attributes", 'dtype': 'float32', 'ragged': True},
                                {'shape': (None, 2), 'name': "edge_indices", 'dtype': 'int64', 'ragged': True}],
                     'input_embedding': {"node_attributes": {"input_dim": 95, "output_dim": 64},
                                         "edge_attributes": {"input_dim": 5, "output_dim": 64}},
                     'output_embedding': 'graph',
                     'output_mlp': {"use_bias": [True, True, False], "units": [25, 10, 1],
                                    "activation": ['relu', 'relu', 'sigmoid']},
                     'attention_args': {"units": 32, "use_final_activation": False, "use_edge_features": True,
                                        "has_self_loops": True, "activation": "kgcnn>leaky_relu", "use_bias": True},
                     'pooling_nodes_args': {'pooling_method': 'mean'},
                     'depth': 3, 'attention_heads_num': 5,
                     'attention_heads_concat': False, 'verbose': 1
                     }
    m = update_model_kwargs_logic(model_default, model_args)
    if m['verbose'] > 0:
        print("INFO:kgcnn: Updated functional make model kwargs:")
        pprint.pprint(m)

    # Local variables for model args
    inputs = m['inputs']
    input_embedding = m['input_embedding']
    output_embedding = m['output_embedding']
    output_mlp = m['output_mlp']
    attention_args = m['attention_args']
    pooling_nodes_args = m['pooling_nodes_args']
    depth = m['depth']
    attention_heads_num = m['attention_heads_num']
    attention_heads_concat = m['attention_heads_concat']

    # Make input
    node_input = ks.layers.Input(**inputs[0])
    edge_input = ks.layers.Input(**inputs[1])
    edge_index_input = ks.layers.Input(**inputs[2])

    # Embedding, if no feature dimension
    n = generate_node_embedding(node_input, inputs[0]['shape'], input_embedding[inputs[0]['name']])
    ed = generate_edge_embedding(edge_input, inputs[1]['shape'], input_embedding[inputs[1]['name']])
    edi = edge_index_input

    # Model
    nk = Dense(units=attention_args["units"], activation="linear")(n)
    for i in range(0, depth):
        heads = [AttentionHeadGATV2(**attention_args)([nk, ed, edi]) for _ in range(attention_heads_num)]
        if attention_heads_concat:
            nk = Concatenate(axis=-1)(heads)
        else:
            nk = Average()(heads)
            nk = Activation(activation=attention_args["activation"])(nk)
    n = nk

    # Output embedding choice
    if output_embedding == 'graph':
        out = PoolingNodes(**pooling_nodes_args)(n)
        out = MLP(**output_mlp)(out)
        main_output = ks.layers.Flatten()(out)  # will be dense
    elif output_embedding == 'node':
        out = MLP(**output_mlp)(n)
        main_output = ChangeTensorType(input_tensor_type="ragged", output_tensor_type="tensor")(out)
    else:
        raise ValueError("Unsupported graph embedding for `GATv2`")

    # Define model output
    model = tf.keras.models.Model(inputs=[node_input, edge_input, edge_index_input], outputs=main_output)
    return model
