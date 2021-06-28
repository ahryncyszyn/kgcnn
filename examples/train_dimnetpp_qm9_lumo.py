import time

import matplotlib as mpl
import numpy as np
import tensorflow as tf
import tensorflow_addons as tfa

mpl.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from kgcnn.utils.learning import LinearWarmupExponentialDecay
from kgcnn.data.datasets.qm9 import QM9Dataset
from kgcnn.literature.DimeNetPP import make_dimnet_pp
from kgcnn.utils.data import ragged_tensor_from_nested_numpy

# Download and generate dataset.
# QM9 has about 200 MB of data
# You need at least 10 GB of RAM to load and process full dataset into memory.
datasets = QM9Dataset()
labels, nodes, _, edge_indices, _ = datasets.get_graph(do_invert_distance=False,
                                                       max_distance=5,
                                                       max_neighbours=20,
                                                       do_gauss_basis_expansion=False,
                                                       max_mols=10000)  # max is 133885
coord = datasets.coord[:10000]
edge_indices, _, angle_indices = datasets.get_angle_index(edge_indices)

# Select LUMO as target and convert into eV from H
labels = labels[:, 7:8] * 27.2114
data_unit = 'eV'

# Train Test split
labels_train, labels_test, nodes_train, nodes_test, coord_train, coord_test, edge_indices_train, edge_indices_test, angle_indices_train, angle_indices_test = train_test_split(
    labels, nodes, coord, edge_indices, angle_indices, test_size=0.10, random_state=42)
del labels, nodes, coord, edge_indices, angle_indices  # Free memory after split, if possible

# Convert to tf.RaggedTensor or tf.tensor
# a copy of the data is generated by ragged_tensor_from_nested_numpy()
nodes_train, coord_train, edge_indices_train, angle_indices_train = ragged_tensor_from_nested_numpy(
    nodes_train), ragged_tensor_from_nested_numpy(coord_train), ragged_tensor_from_nested_numpy(
    edge_indices_train), ragged_tensor_from_nested_numpy(angle_indices_train)

nodes_test, coord_test, edge_indices_test, angle_indices_test = ragged_tensor_from_nested_numpy(
    nodes_test), ragged_tensor_from_nested_numpy(coord_test), ragged_tensor_from_nested_numpy(
    edge_indices_test), ragged_tensor_from_nested_numpy(angle_indices_test)

# Standardize output with scikit-learn std-scaler
scaler = StandardScaler(with_std=True, with_mean=True)
labels_train = scaler.fit_transform(labels_train)
labels_test = scaler.transform(labels_test)

# Define input and output data
xtrain = nodes_train, coord_train, edge_indices_train, angle_indices_train
xtest = nodes_test, coord_test, edge_indices_test, angle_indices_test
ytrain = labels_train
ytest = labels_test

# Get Model with matching input and output properties
model = make_dimnet_pp(input_node_shape=[None],
                       input_embedd={'input_node_vocab': 95,
                                     'input_node_embedd': 128,
                                     },
                       num_targets=1,
                       extensive=False,
                       cutoff=5.0,
                       )

# Define learning rate and epochs
learning_rate=1e-3
warmup_steps=3000
decay_steps=4000000
decay_rate=0.01
ema_decay=0.999
epo = 900
epostep = 10
# max_grad_norm=10.0

learn_dec = LinearWarmupExponentialDecay(learning_rate, warmup_steps, decay_steps, decay_rate)
optimizer = tf.keras.optimizers.Adam(learning_rate=learn_dec, amsgrad=True)
optimizer_ma = tfa.optimizers.MovingAverage(optimizer, average_decay=ema_decay)
cbks = []
model.compile(loss='mean_squared_error',
              optimizer=optimizer_ma,
              metrics=['mean_absolute_error'])
print(model.summary())

# Start training
start = time.process_time()
hist = model.fit(xtrain, ytrain,
                 epochs=epo,
                 batch_size=32,
                 callbacks=[],
                 validation_freq=epostep,
                 validation_data=(xtest, ytest),
                 verbose=2
                 )
stop = time.process_time()
print("Print Time for taining: ", stop - start)

# Extract training statistics
trainloss = np.array(hist.history['mean_absolute_error'])
testloss = np.array(hist.history['val_mean_absolute_error'])

# Predict lumo with model
pred_test = scaler.inverse_transform(model.predict(xtest))
true_test = scaler.inverse_transform(ytest)
mae_valid = np.mean(np.abs(pred_test - true_test))

# Plot loss vs epochs
plt.figure()
plt.plot(np.arange(trainloss.shape[0]), trainloss, label='Training Loss', c='blue')
plt.plot(np.arange(epostep, epo + epostep, epostep), testloss, label='Test Loss', c='red')
plt.scatter([trainloss.shape[0]], [mae_valid], label="{0:0.4f} ".format(mae_valid) + "[" + data_unit + "]", c='red')
plt.xlabel('Epochs')
plt.ylabel('Loss ' + "[" + data_unit + "]")
plt.title('DimeNet++ Loss')
plt.legend(loc='upper right', fontsize='x-large')
plt.savefig('dimnet_loss.png')
plt.show()

# Predicted vs Actual
plt.figure()
plt.scatter(pred_test, true_test, alpha=0.3, label="MAE: {0:0.4f} ".format(mae_valid) + "[" + data_unit + "]")
plt.plot(np.arange(np.amin(true_test), np.amax(true_test), 0.05),
         np.arange(np.amin(true_test), np.amax(true_test), 0.05), color='red')
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.legend(loc='upper left', fontsize='x-large')
plt.savefig('dimnet_predict.png')
plt.show()
