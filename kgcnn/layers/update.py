import tensorflow as tf

from kgcnn.layers.base import GraphBaseLayer


@tf.keras.utils.register_keras_serializable(package='kgcnn', name='GRUUpdate')
class GRUUpdate(GraphBaseLayer):
    """Gated recurrent unit for updating embeddings. First proposed by `NMPNN <http://arxiv.org/abs/1704.01212>`__ .

    Args:
        units (int): Units for GRU.
        activation: Activation function to use. Default: hyperbolic tangent
            (`tanh`). If you pass None, no activation is applied
            (ie. "linear" activation: `a(x) = x`).
        recurrent_activation: Activation function to use for the recurrent step.
            Default: sigmoid (`sigmoid`). If you pass `None`, no activation is
            applied (ie. "linear" activation: `a(x) = x`).
        use_bias: Boolean, (default `True`), whether the layer uses a bias vector.
        kernel_initializer: Initializer for the `kernel` weights matrix,
            used for the linear transformation of the inputs. Default:
            `glorot_uniform`.
        recurrent_initializer: Initializer for the `recurrent_kernel`
            weights matrix, used for the linear transformation of the recurrent state.
            Default: `orthogonal`.
        bias_initializer: Initializer for the bias vector. Default: `zeros`.
        kernel_regularizer: Regularizer function applied to the `kernel` weights
            matrix. Default: `None`.
        recurrent_regularizer: Regularizer function applied to the
            `recurrent_kernel` weights matrix. Default: `None`.
        bias_regularizer: Regularizer function applied to the bias vector. Default:
            `None`.
        kernel_constraint: Constraint function applied to the `kernel` weights
            matrix. Default: `None`.
        recurrent_constraint: Constraint function applied to the `recurrent_kernel`
            weights matrix. Default: `None`.
        bias_constraint: Constraint function applied to the bias vector. Default:
            `None`.
        dropout: Float between 0 and 1. Fraction of the units to drop for the
            linear transformation of the inputs. Default: 0.
        recurrent_dropout: Float between 0 and 1. Fraction of the units to drop for
            the linear transformation of the recurrent state. Default: 0.
        reset_after: GRU convention (whether to apply reset gate after or
            before matrix multiplication). False = "before",
            True = "after" (default and CuDNN compatible).
    """

    def __init__(self, units,
                 activation='tanh', recurrent_activation='sigmoid',
                 use_bias=True, kernel_initializer='glorot_uniform',
                 recurrent_initializer='orthogonal',
                 bias_initializer='zeros', kernel_regularizer=None,
                 recurrent_regularizer=None, bias_regularizer=None, kernel_constraint=None,
                 recurrent_constraint=None, bias_constraint=None, dropout=0.0,
                 recurrent_dropout=0.0, reset_after=True,
                 **kwargs):
        """Initialize layer."""
        super(GRUUpdate, self).__init__(**kwargs)
        self.units = units

        self.gru_cell = tf.keras.layers.GRUCell(units=units,
                                                activation=activation, recurrent_activation=recurrent_activation,
                                                use_bias=use_bias, kernel_initializer=kernel_initializer,
                                                recurrent_initializer=recurrent_initializer,
                                                bias_initializer=bias_initializer,
                                                kernel_regularizer=kernel_regularizer,
                                                recurrent_regularizer=recurrent_regularizer,
                                                bias_regularizer=bias_regularizer,
                                                kernel_constraint=kernel_constraint,
                                                recurrent_constraint=recurrent_constraint,
                                                bias_constraint=bias_constraint,
                                                dropout=dropout,
                                                recurrent_dropout=recurrent_dropout, reset_after=reset_after)

    def build(self, input_shape):
        """Build layer."""
        super(GRUUpdate, self).build(input_shape)

    def call(self, inputs, mask=None, **kwargs):
        """Forward pass.

        Args:
            inputs (list): [nodes, updates]

                - nodes (tf.RaggedTensor): Node embeddings of shape (batch, [N], F)
                - updates (tf.RaggedTensor): Matching node updates of shape (batch, [N], F)
            mask: Mask for inputs. Default is None.

        Returns:
           tf.RaggedTensor: Updated nodes of shape (batch, [N], F)
        """
        inputs = self.assert_ragged_input_rank(inputs, ragged_rank=1, mask=mask)
        n, npart = inputs[0].values, inputs[0].row_splits
        eu, _ = inputs[1].values, inputs[1].row_splits
        out, _ = self.gru_cell(eu, n, **kwargs)
        out = tf.RaggedTensor.from_row_splits(out, npart, validate=self.ragged_validate)
        return out

    def get_config(self):
        """Update layer config."""
        config = super(GRUUpdate, self).get_config()
        conf_cell = self.gru_cell.get_config()
        param_list = ["units", "activation", "recurrent_activation",
                      "use_bias", "kernel_initializer",
                      "recurrent_initializer",
                      "bias_initializer", "kernel_regularizer",
                      "recurrent_regularizer", "bias_regularizer", "kernel_constraint",
                      "recurrent_constraint", "bias_constraint", "dropout",
                      "recurrent_dropout", "reset_after"]
        for x in param_list:
            config.update({x: conf_cell[x]})
        return config