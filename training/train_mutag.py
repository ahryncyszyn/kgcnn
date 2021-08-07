import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import time
import os

from kgcnn.utils.learning import LinearLearningRateScheduler
from sklearn.model_selection import KFold
from kgcnn.data.datasets.mutag import MUTAGDataset
from kgcnn.io.loader import NumpyTensorList
from kgcnn.utils.models import ModelSelection


# Hyper and model
ms = ModelSelection()
make_model, hyper = ms.make_model("Unet", "MUTAG")

# Loading PROTEINS Dataset
dataset = MUTAGDataset()
data_name = dataset.dataset_name
data_length = dataset.length

# Data-set split
kf = KFold(n_splits=5, random_state=None, shuffle=True)
split_indices = kf.split(X=np.arange(data_length)[:, None])

dataloader = NumpyTensorList(*[getattr(dataset, x['name']) for x in hyper['model']['inputs']])
labels = np.expand_dims(dataset.graph_labels, axis=-1)

# Set learning rate and epochs
hyper_train = hyper['training']
epo = hyper_train['fit']['epochs']
epostep = hyper_train['fit']['validation_freq']
batch_size = hyper_train['fit']['batch_size']

train_loss = []
test_loss = []
acc_5fold = []
for train_index, test_index in split_indices:
    model = make_model(**hyper['model'])

    is_ragged = [x['ragged'] for x in hyper['model']['inputs']]
    xtrain, ytrain = dataloader[train_index].tensor(ragged=is_ragged), labels[train_index]
    xtest, ytest = dataloader[test_index].tensor(ragged=is_ragged), labels[test_index]

    # Compile model with optimizer and loss
    optimizer = tf.keras.optimizers.get(hyper_train['optimizer'])
    cbks = [tf.keras.utils.deserialize_keras_object(x) for x in hyper_train['callbacks']]
    model.compile(loss='binary_crossentropy',
                  optimizer=optimizer,
                  weighted_metrics=['accuracy'])
    print(model.summary())

    # Start and time training
    start = time.process_time()
    hist = model.fit(xtrain, ytrain,
                     validation_data=(xtest, ytest),
                     callbacks=[cbks],
                     **hyper_train['fit'],
                     )
    stop = time.process_time()
    print("Print Time for taining: ", stop - start)

    # Get loss from history
    train_loss.append(np.array(hist.history['accuracy']))
    val_acc = np.array(hist.history['val_accuracy'])
    test_loss.append(val_acc)
    acc_valid = np.mean(val_acc[-5:])
    acc_5fold.append(acc_valid)

os.makedirs(data_name, exist_ok=True)
filepath = os.path.join(data_name, hyper['model']['name'])
os.makedirs(filepath, exist_ok=True)

# Plot loss vs epochs
plt.figure()
for x in train_loss:
    plt.plot(np.arange(x.shape[0]), x, c='red', alpha=0.85)
for y in test_loss:
    plt.plot((np.arange(len(y)) + 1) * epostep, y, c='blue', alpha=0.85)
plt.scatter([train_loss[-1].shape[0]], [np.mean(acc_5fold)],
            label=r"Test: {0:0.4f} $\pm$ {1:0.4f}".format(np.mean(acc_5fold), np.std(acc_5fold)), c='blue')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.title('MUTAG Loss')
plt.legend(loc='upper right', fontsize='large')
plt.savefig(os.path.join(filepath, 'acc_mutag.png'))
plt.show()

# Save model
model.save(os.path.join(filepath, "model"))

# save splits
all_test_index = []
for train_index, test_index in split_indices:
    all_test_index.append([train_index, test_index])
np.savez(os.path.join(filepath, "kfold_splits.npz"), all_test_index)