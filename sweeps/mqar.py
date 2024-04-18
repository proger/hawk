"""
How do different models perform on the multi-query associative recall task?
"""
from pathlib import Path
import torch
import wandb

from train import train, parser, device
from train_tape import Tapes
from hippogriff import GriffinLM, GriffinConfig
from multiquery_ar import multiquery_ar

WANDB_PROJECT = 'hippogriff-mqar'

def run():
    wandb.init(project=WANDB_PROJECT)

    # how to nicely merge args and wandb.config?
    args = parser.parse_args()
    args.exp = Path(args.exp.substitute(**vars(args)))
    args.exp.mkdir(parents=True, exist_ok=True)
    args.lr = wandb.config.lr

    vocab_size = wandb.config.vocab_size
    batch_size = wandb.config.batch_size
    num_train_batches = 100_000 // batch_size
    num_valid_batches = 3_000 // batch_size
    seq_len = wandb.config.seq_len
    num_kv_pairs = wandb.config.num_kv_pairs
    train_inputs, train_targets = multiquery_ar(vocab_size=vocab_size, num_examples=num_train_batches*batch_size, input_seq_len=seq_len, seed=42, power_a=0.01, num_kv_pairs=num_kv_pairs, random_non_queries=False)
    valid_inputs, valid_targets = multiquery_ar(vocab_size=vocab_size, num_examples=num_valid_batches*batch_size, input_seq_len=seq_len, seed=43, power_a=0.01, num_kv_pairs=num_kv_pairs, random_non_queries=False)

    class Repeat:
        def __init__(self, xs):
            self.xs = xs

        def __getitem__(self, i):
            return self.xs[i % len(self.xs)]
    
    tapes = Tapes(
        vocab_size=vocab_size,
        seq_len=seq_len,
        train=Repeat([(input, target) for input, target in zip(train_inputs.to(device).view(num_train_batches, batch_size, seq_len),
                                                               train_targets.to(device).view(num_train_batches, batch_size, seq_len))]),
        valid=[(input, target) for input, target in zip(valid_inputs.to(device).view(num_valid_batches, batch_size, seq_len),
                                                        valid_targets.to(device).view(num_valid_batches, batch_size, seq_len))],
    )
    print('mqar: one epoch takes', len(tapes.train.xs), 'steps')

    torch.manual_seed(wandb.config.seed)

    dim = wandb.config.dim
    match wandb.config.model.split('_'):
        case ['hawk']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   conv_kernel_size=4, hawk_expansion_factor=1)
        case ['hawk', 'noconv']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        # all s6 variants have conv turned off for now
        case ['s6', 'dstate1']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   time_module='S6', state_expansion=1,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['s6', 'dstate2']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0,
                                   time_module='S6', state_expansion=2, dim=dim,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['s6', 'dstate4']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0,
                                   time_module='S6', state_expansion=4, dim=dim,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['s6', 'dstate8']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0,
                                   time_module='S6', state_expansion=8, dim=dim,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['s6', 'dstate16']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0,
                                   time_module='S6', state_expansion=16, dim=dim,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['s6', 'dstate32']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0,
                                   time_module='S6', state_expansion=32, dim=dim,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['s6', 'dstate64']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0,
                                   time_module='S6', state_expansion=64, dim=dim,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['qlstm']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   time_module='TiedQuasiLSTM', tied_quasi_lstm_num_heads=dim,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['qlstm', 'tied8']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   time_module='TiedQuasiLSTM', tied_quasi_lstm_num_heads=8,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['qlstm', 'tied16']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   time_module='TiedQuasiLSTM', tied_quasi_lstm_num_heads=16,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['qlstm', 'tied32']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   time_module='TiedQuasiLSTM', tied_quasi_lstm_num_heads=32,
                                   conv_kernel_size=0, hawk_expansion_factor=1)
        case ['outer', n, 'value']:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   time_module='OuterProduct', tied_quasi_lstm_num_heads=int(n),
                                   conv_kernel_size=0, hawk_expansion_factor=1, outer_query_values=True)
        case ['outer', n]:
            config = GriffinConfig(vocab_size=vocab_size, num_layers=wandb.config.num_layers, smqa_head_dim=0, dim=dim,
                                   time_module='OuterProduct', tied_quasi_lstm_num_heads=int(n),
                                   conv_kernel_size=0, hawk_expansion_factor=1)
    model = GriffinLM(config).to(device)
    wandb.config.parameters = sum(p.numel() for p in model.parameters())
    if config.time_module == 'OuterProduct':
        state_size = (config.dim // config.tied_quasi_lstm_num_heads)**2 * config.tied_quasi_lstm_num_heads
    else:
        state_size = config.dim
    wandb.config.state_size = sum([config.hawk_expansion_factor * config.state_expansion * state_size for _ in range(config.num_layers)])
    wandb.watch(model, log='all')

    opt = torch.optim.AdamW(model.parameter_groups(), lr=args.lr, betas=(0.9, 0.999), fused=False)
    train(model, tapes, opt, args=args)


sweep_configuration = {
    "name": "mqar(8kv+16kv)*5(s6+outer+values)*4lr*3seeds",
    "method": "grid",
    "metric": {"goal": "maximize", "name": "eval/accuracy"},
    "parameters": {
        #"model": {"values": ["hawk_noconv", "s6_dstate1", "s6_dstate4", "s6_dstate8", "s6_dstate16", "qlstm", "qlstm_tied8", "qlstm_tied16"]},
        "model": {"values": [#"hawk_noconv",
                             "s6_dstate1", # 64 state
                             "s6_dstate2", # 128 state
                             "s6_dstate4", # 256 state
                             "s6_dstate8", # 512 state
                             "s6_dstate16", # 1024 state
                             "outer_64", "outer_64_value", # 64 state
                             "outer_32", "outer_32_value", # 128 state
                             "outer_16", "outer_16_value", # 256 state
                             "outer_8", "outer_8_value", # 512 state
                             "outer_4", "outer_4_value" # 1024 state
                             ]},
        #"model": {"values": ["outer_8", "outer_8_value", "outer_4", "outer_4_value"]},
        #"dim": {"values": [64, 128, 256, 512]},
        "dim": {"values": [64]},
        "num_layers": {"values": [2]},
        "lr": {"values": [2e-3, 1e-3, 3e-4, 1e-4]},
        #"lr": {"values": [2e-3]},
        "seed": {"values": [1,2,3]},
        "vocab_size": {"values":[64]},
        "batch_size": {"values":[64]},
        "seq_len": {"values":[64]},
        "num_kv_pairs": {"values":[8,16]},
    },
}

if __name__ == '__main__':
    sweep_id = wandb.sweep(sweep=sweep_configuration, project=WANDB_PROJECT)
    wandb.agent(sweep_id, function=run)


