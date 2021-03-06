import tensorflow as tf
import numpy as np
from data_preprocess import data_iterator

en_file_sources = ["http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2008.en.shuffled.gz", "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2009.en.shuffled.gz", "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2010.en.shuffled.gz",
                   "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2011.en.shuffled.gz", "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2012.en.shuffled.gz", "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2013.en.shuffled.gz", "http://www.statmt.org/wmt15/training-monolingual-news-crawl-v2/news.2014.en.shuffled.v2.gz"]
fr_file_sources = ["http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2008.fr.shuffled.gz", "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2009.fr.shuffled.gz", "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2010.fr.shuffled.gz",
                   "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2011.fr.shuffled.gz", "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2012.fr.shuffled.gz", "http://www.statmt.org/wmt14/training-monolingual-news-crawl/news.2013.fr.shuffled.gz", "http://www.statmt.org/wmt15/training-monolingual-news-crawl-v2/news.2014.fr.shuffled.v2.gz"]

en_file_paths = ["data/en_%d.gz" %
                 i for i in range(0, len(en_file_sources))]
fr_file_paths = ["data/fr_%d.gz" %
                 i for i in range(0, len(fr_file_sources))]

en_val_subset_file_path = "data/en_val_subset.gz"
fr_val_subset_file_path = "data/fr_val_subset.gz"

en_onehot_tok_idx = "data/en_onehot.npy"
fr_onehot_tok_idx = "data/fr_onehot.npy"

onehot_tok_idx = np.load(fr_onehot_tok_idx).item()

# Build LSTM graph
def length(sequence):
    used = tf.sign(tf.reduce_max(tf.abs(sequence), reduction_indices=2))
    length = tf.reduce_sum(used, reduction_indices=1)
    length = tf.cast(length, tf.int32)
    return length

vocab_size = len(onehot_tok_idx)
num_layers = 4
num_steps = 48
batch_size = 384
hidden_size = 250

# tensor of shape [ batch_size x num_steps x vocab_size ] with post-padding
encoder_inputs = tf.placeholder(tf.float32, shape=(
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
    [hidden_size, vocab_size], stddev=0.05, dtype=tf.float32))
decoder_bias = tf.Variable(
    tf.constant(1, shape=[vocab_size], dtype=tf.float32))

# list of 1D tensors [ batch_size ] of length num_steps
raw_labels = tf.placeholder(tf.int32, shape=(
    batch_size, num_steps), name="placeholder_raw_labels")
targets = tf.unstack(raw_labels, axis=1)

# list of 1D tensors [ batch_size ] of length num_steps
loss_weights = tf.unstack(tf.cast(mask, tf.float32), axis=1)

# dropout
dropout = tf.placeholder(tf.float32, name="placeholder_dropout")

lstm = tf.contrib.rnn.BasicLSTMCell(
    hidden_size, forget_bias=1, state_is_tuple=True)
lstm = tf.contrib.rnn.DropoutWrapper(lstm, output_keep_prob=dropout)
stacked_lstm = tf.contrib.rnn.MultiRNNCell(
    [lstm] * num_layers, state_is_tuple=True)

initial_state = stacked_lstm.zero_state(batch_size, dtype=tf.float32)

encoder_outputs, encoder_state = tf.nn.dynamic_rnn(
    cell=stacked_lstm, inputs=encoder_inputs, initial_state=initial_state, dtype=tf.float32, sequence_length=encoder_lengths)

decoder_outputs, decoder_state = tf.contrib.legacy_seq2seq.rnn_decoder(
    decoder_inputs=decoder_inputs, initial_state=encoder_state, cell=stacked_lstm)

preds = [tf.matmul(step, decoder_weights) +
         decoder_bias for step in decoder_outputs]

loss = tf.contrib.legacy_seq2seq.sequence_loss(
    logits=preds, targets=targets, weights=loss_weights)

# optimizer = tf.train.GradientDescentOptimizer(.01)
optimizer = tf.train.AdamOptimizer(.001)
gradients = optimizer.compute_gradients(loss)
clipped_gradients = [(tf.clip_by_norm(grad, 5), var) for grad, var in gradients]
train_op = optimizer.apply_gradients(clipped_gradients)

print("graph loaded")

iter_ = data_iterator([fr_file_paths[6]], onehot_tok_idx, 1, batch_size, num_steps)

val_iter_ = data_iterator([fr_val_subset_file_path], onehot_tok_idx, 1, batch_size, num_steps)

print("iterator loaded")

saver = tf.train.Saver(max_to_keep=10)

init = tf.global_variables_initializer()

print("variables initialized")

total_train_samples = 1000000
total_val_samples = 3000

epoch_iterations = int(total_train_samples / batch_size)
total_iterations = epoch_iterations * 10
val_iterations = int(total_val_samples / batch_size)

print_train_iterations = 10
print_val_iterations = int(epoch_iterations / 20)

train_keep_prob = .7

with tf.Session() as sess:
    sess.run(init)

    train_accuracy = 0

    for i in range(total_iterations):
        sequences_batch, labels_batch = iter_.__next__()
        
        train_accuracy += loss.eval(session=sess, feed_dict={
                                   encoder_inputs: sequences_batch, raw_labels: labels_batch, dropout: 1.0})
        
        if (i + 1) % print_val_iterations == 0:

            validation_accuracy = 0

            for j in range(0, val_iterations):

                val_sequences_batch, val_labels_batch = val_iter_.__next__()

                validation_accuracy += loss.eval(session=sess, feed_dict={
                                           encoder_inputs: val_sequences_batch, raw_labels: val_labels_batch, dropout: 1.0})

            validation_accuracy /= val_iterations

            print("step %d, validation loss %g" % (i + 1, validation_accuracy))

        if (i + 1) % epoch_iterations == 0:
            save_path = saver.save(sess, "tmp/model_%d.ckpt"%(i + 1))
            print("Model saved in file: %s"%save_path)

        if (i + 1) % print_train_iterations == 0:
            train_accuracy /= print_train_iterations
            print("step %d, training loss %g" % (i + 1, train_accuracy))
            train_accuracy = 0

        train_op.run(session=sess, feed_dict={
                     encoder_inputs: sequences_batch, raw_labels: labels_batch, dropout: train_keep_prob})
