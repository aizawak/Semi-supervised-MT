# Wiki Data Dump
# https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2

# Amazon Product Reviews
# https://snap.stanford.edu/data/web-Amazon.htmls

# Book Data
# English Books
# http://opus.lingfil.uu.se/download.php?f=Books/en.tar.gz
# French Books
# http://opus.lingfil.uu.se/download.php?f=Books/fr.tar.gz

# English movie subtitles
# http://opus.lingfil.uu.se/download.php?f=OpenSubtitles2016/mono/OpenSubtitles2016.raw.en.gz

# French movie subtitles
# http://opus.lingfil.uu.se/download.php?f=OpenSubtitles2016/mono/OpenSubtitles2016.raw.fr.gz   

import numpy as np
import os
from random import shuffle
import re
import collections
import urllib.request
import gzip
import math

def read_data(file_path, write_path, num_batches):
    
    with gzip.open(file_path, 'rb') as f:
            content = f.read()

    onehot_tok_idx = {}
    
    tok_idx=0

    for i in range(0, num_batches):
        
        start = math.floor(i * len(content) / num_batches)
        end = math.floor((i + 1) * len(content) / num_batches)

        sent = content[start:end].decode('utf-8').split('\n')
        del content
        
        print("...subtitles in memory for batch %d/%d"%(i+1, num_batches))

        for sent_idx in range(0, len(sent)):

            sent_tok = re.findall(r"[\w]+|[^\s\w]", sent[sent_idx])

            for tok in sent_tok:
                if tok not in onehot_tok_idx_en:
                    onehot_tok_idx[tok]=tok_idx
                    tok_idx+=1

        del sent

        print("...token id's assigned for batch %d/%d"%(i+1,num_batches))

    np.save(write_path, onehot_tok_idx)
    print("...token id's saved")

def data_iterator(file_path, onehot_tok_idx, num_batches, batch_size, seq_length):

    with gzip.open(file_path, 'rb') as f:
        content = f.read()

    while True:
        for i in range(0, num_batches):

            start = math.floor(i * len(content) / num_batches)
            end = math.floor((i + 1) * len(content) / num_batches)

            sent = content[start:end].decode('utf-8').split('\n')

            onehot_seq_batch = np.empty(shape=(seq_length, batch_size, len(onehot_tok_idx)), dtype="float16")

            for batch_idx in range(0, int(len(sent)/batch_size)):

                for sent_idx in range(batch_idx*batch_size, (batch_idx+1)*batch_size):

                    sent_tok = re.findall(r"[\w]+|[^\s\w]")

                    seq_idx = len(seq_length) - 1

                    for tok_idx in range(len(sent_tok) - 1, -1, -1):

                        tok = sent_tok[tok_idx]

                        if tok not in onehot_tok_idx:
                            continue
                        
                        onehot_seq_batch[seq_idx][batch_idx][onehot_tok_idx[tok]] = 1
                    yield onehot_seq_batch

en_file_path = "data/english_subtitles.gz"
fr_file_path = "data/french_subtitles.gz"

en_write_path = "data/en_onehot.npy"
fr_write_path = "data/fr_onehot.npy"

num_batches = 5

print("processing english subtitles")

if not os.path.isfile(en_file_path):
    urllib.request.urlretrieve("http://opus.lingfil.uu.se/download.php?f=OpenSubtitles2016/mono/OpenSubtitles2016.raw.en.gz", filename=en_file_path)

print("...subtitles downloaded")

generate_data(en_file_path, en_write_path, num_batches)


print("processing french subtitles")

if not os.path.isfile(fr_file_path):
    urllib.request.urlretrieve("http://opus.lingfil.uu.se/download.php?f=OpenSubtitles2016/mono/OpenSubtitles2016.raw.fr.gz", filename=fr_file_path)
    
print("...subtitles downloaded")

generate_data(fr_file_path, fr_write_path, num_batches)