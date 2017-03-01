import tensorflow as tf
import numpy as np
from data_preprocess import data_iterator

# english
# onehot_tok_idx = np.load('data/en_onehot.npy')
# en_file_path = "data/english_subtitles.gz"


# french
onehot_tok_idx = np.load('data/fr_onehot.npy').item()
fr_file_path = "data/french_subtitles.gz"

# Build LSTM graph
def length(sequence):
    used = tf.sign(tf.reduce_max(tf.abs(sequence), reduction_indices=2))
    length = tf.reduce_sum(used, reduction_indices=1)
    length = tf.cast(length, tf.int32)
    return length

vocab_size = len(onehot_tok_idx)
num_layers = 4
num_steps = 50
batch_size = 20
hidden_size = 1000

# tensor of shape [ batch_size x num_steps x vocab_size ] with post-padding
encoder_inputs = tf.placeholder(tf.float16, shape=(
    batch_size, num_steps, vocab_size), name="placeholder_encoder_inputs")

# tensor of shape [ batch_size x num_steps ]
mask = tf.sign(tf.reduce_max(tf.abs(encoder_inputs), axis=2))

# tensor of shape [ batch_size ]
encoder_lengths = tf.cast(tf.reduce_sum(
    mask, reduction_indices=1), tf.int32)

# list of 2D tensors [ batch_size x vocab_size ] of length num_steps
decoder_inputs = tf.unstack(tf.transpose(encoder_inputs, [1, 0, 2]), axis=0)
decoder_inputs = (
    [tf.zeros_like(decoder_inputs[0], name="GO")] + decoder_inputs[:-1])

decoder_weights = tf.Variable(tf.truncated_normal(
    [hidden_size, vocab_size], stddev=0.05, dtype=tf.float16))
decoder_bias = tf.Variable(
    tf.constant(.1, shape=[vocab_size], dtype=tf.float16))

# list of 1D tensors [ batch_size ] of length num_steps
raw_labels = tf.placeholder(tf.int32, shape=(
    batch_size, num_steps), name="placeholder_raw_labels")
labels = tf.unstack(raw_labels, axis=1)

# list of 1D tensors [ batch_size ] of length num_steps
loss_weights = tf.unstack(tf.cast(mask, tf.float16), axis=1)

lstm = tf.contrib.rnn.BasicLSTMCell(
    hidden_size, forget_bias=0.0, state_is_tuple=True)
stacked_lstm = tf.contrib.rnn.MultiRNNCell(
    [lstm] * num_layers, state_is_tuple=True)

initial_state = stacked_lstm.zero_state(batch_size, dtype=tf.float16)

encoder_outputs, encoder_state = tf.nn.dynamic_rnn(
    cell=stacked_lstm, inputs=encoder_inputs, initial_state=initial_state, dtype=tf.float16, sequence_length=encoder_lengths)

decoder_outputs, decoder_state = tf.contrib.legacy_seq2seq.rnn_decoder(
    decoder_inputs=decoder_inputs, initial_state=encoder_state, cell=stacked_lstm)

preds = [tf.matmul(step, decoder_weights) +
         decoder_bias for step in decoder_outputs]

loss = tf.contrib.legacy_seq2seq.sequence_loss(
    logits=preds, targets=labels, weights=loss_weights)

optimizer = tf.train.AdamOptimizer(1e-6)
gradients = optimizer.compute_gradients(loss)
clipped_gradients = [(tf.clip_by_norm(grad, 2), var) for grad, var in gradients]
train_op = optimizer.apply_gradients(clipped_gradients)

print("graph loaded")

iter_ = data_iterator(fr_file_path, onehot_tok_idx, 1, batch_size, num_steps)

print("iterator loaded")

saver = tf.train.Saver()

init = tf.global_variables_initializer()

print("variables initialized")

with tf.Session() as sess:
    sess.run(init)
    for i in range(200000):
        sequences_batch, labels_batch = iter_.__next__()

        if (i + 1) % 10000 == 0:
            save_path = saver.save(sess, "tmp/model_%d.ckpt"%(i+1))
            print("Model saved in file: %s"%save_path)

        if (i + 1) % 100 == 0:
            train_accuracy = loss.eval(session=sess, feed_dict={
                                       encoder_inputs: sequences_batch, raw_labels: labels_batch})
            print("step %d, training loss %g" % (i + 1, train_accuracy))

        train_op.run(session=sess, feed_dict={
                     encoder_inputs: sequences_batch, raw_labels: labels_batch})
