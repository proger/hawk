#
# @article{zoology2023,
#   title={Zoology: Measuring and Improving Recall in Efficient Language Models},
#   author={Arora, Simran and Eyuboglu, Sabri and Timalsina, Aman and Johnson, Isys and Poli, Michael and Zou, James and Rudra, Atri and Ré, Christopher},
#   journal={arXiv:2312.04927},
#   year={2023}
# }
# Licensed under Apache 2.0
# https://github.com/HazyResearch/zoology/blob/main/LICENSE.md
#

import numpy as np
import torch


def multiquery_ar(
    vocab_size: int = 64,
    num_examples: int = 100_000,
    input_seq_len: int = 64,
    seed: int = 42,
    power_a: float = 0.01,
    num_kv_pairs: int = 8,
    random_non_queries: bool = False,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Generates synthetic data for the multi-query associative recall task as described in
    Arora,Eyuboglu, et al. "Zoology: Measuring and improving recall in efficient language models.".

    Example: 
        `multiquery_ar(vocab_size=12, num_kv_pairs=2, input_seq_len=16, random_non_queries=False)` 
        will generate input and label sequences of the form: 
                
                Key   Val  Key  Val            Query                         Query
        Inputs: 2     8    4    7    0    0    4    0    0    0    0    0    2    0    0 
        Labels: -100 -100 -100 -100 -100 -100  7    -100 -100 -100 -100 -100 8    -100 -100

        The -100 labels are ignored by the loss function and metrics.
    
    We include one important note on the power law distribution. In real language data, 
    the gap between repeated bigrams follows a power law. Intuitively, if the bigram
    "common buzzard" appears in text, the probability of the bigram appearing again 
    drops the further away from the orginal mention we are. In our synthetic, we can 
    control this with the power law parameters `train_power_a` and `test_power_a`. 
    Setting these to 1.0 will result in a uniform distribution. You can visualize the
    distribution with the following code:
    ```
    space = 100
    power_a = 0.01  
    p = power_a * np.arange(1, space + 1) ** (power_a-1)
    p = p / p.sum()
    plt.plot(p)
    ```

    Args:
        vocab_size (int): The size of the vocabulary. As discussed in the Zoology 
            paper, large vocabulary sizes (>1k) can be important for highlighting 
            differences between model architectures. Defaults to 8_192.
        num_examples (int): The number of training examples to generate. Defaults 
            to 100_000.
        input_seq_len (int): The length of the input sequence. Defaults to 64. In 
            In Figure 2 of the Zoology paper, we vary the input sequence length from 
            64 to 512 and the number of key-value pairs from 4 to 64.
        seed (int): The seed for the random number generator.
        num_kv_pairs (int): The number of key-value pairs.
        power_a (float, optional): The power for the power law distribution for 
            training data. Defaults to 0.01.
        random_non_queries (bool, optional): If True, replace all the 0's (as in the 
            example above) with random values in the input. Defaults to True.

    Returns:
        inputs: A tensor with input sequences of shape (num_examples, input_seq_len).
        labels: A tensor with label sequences of shape (num_examples, input_seq_len).

    """
    assert input_seq_len % 2 == 0, "input_seq_len must be even"
    assert vocab_size >= input_seq_len
    assert num_kv_pairs * 4 <= input_seq_len

    np.random.seed(seed)

    # two tokens for key and value
    context_size = num_kv_pairs * 2

    # create keys so that each key is present exactly once in each example
    key_vocab_size = vocab_size // 2
    key_choices = np.arange(1, key_vocab_size)
    value_choices = np.arange(key_vocab_size, vocab_size)

    keys_unshuffled = np.tile(key_choices, (num_examples, 1))
    keys = np.apply_along_axis(np.random.choice, 1, keys_unshuffled, replace=False, size=num_kv_pairs)

    values_unshuffled = np.tile(value_choices, (num_examples, 1))
    values = np.apply_along_axis(np.random.choice, 1, values_unshuffled, replace=False, size=num_kv_pairs)

    # create sequences
    kvs = np.zeros((num_examples, context_size), dtype=np.int64)
    kvs[:, 0::2] = keys
    kvs[:, 1::2] = values

    # compute power law
    space = (input_seq_len - context_size) // 2
    p = power_a * np.arange(1, space + 1) ** (power_a-1)
    p = p / p.sum()

    x = np.stack([np.arange(space, dtype=int)] * num_examples)
    gaps = np.apply_along_axis(np.random.choice, axis=1, arr=x, replace=False, p=p, size=num_kv_pairs)

    # queries and answers
    queries = np.zeros((num_examples, input_seq_len - context_size + 1), dtype=np.int64)
    np.put_along_axis(queries, (gaps * 2), values=keys, axis=1)
    examples = np.concatenate([
        kvs, 
        queries
    ], axis=1)

    labels = np.full((num_examples, input_seq_len + 1), -100, dtype=np.int64)
    np.put_along_axis(labels, (gaps * 2) + context_size + 1, values=values, axis=1)

    inputs, labels = torch.tensor(examples[:, :-1]), torch.tensor(labels[:, 1:])
    
    # replace all the 0 with random values
    if random_non_queries:
        inputs[inputs == 0] = torch.randint(vocab_size, size=inputs.shape)[inputs == 0]
    return inputs, labels


if __name__ == '__main__':
    inputs, labels = multiquery_ar()
    print(inputs[0])
    print(labels[0])