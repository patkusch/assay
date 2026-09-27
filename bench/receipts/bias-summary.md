# Label bias summary

Built by `bench/bias_summary.py` from the receipts in `bench/receipts/`. For each system and task, the biggest bias: the label predicted far more often than it is true, whether shuffling the option order made it better or worse, and (for routing and urgency, where every system showed a real bias) the full table.

## Biggest bias per system and task, shuffled condition

| System | Task | Label | Predicted ÷ true | Single order | Shuffled |
|---|---|---|---|---|---|
| assay + gemma3 4B (letter) | routing | `billing` | 2.74x | 2.43x | 2.74x (worse after shuffling) |
| assay + gemma3 4B (letter) | urgency | `3` | 1.71x | 4.07x | 1.71x (better after shuffling) |
| assay + gemma3 4B (word) | routing | `billing` | 2.50x | 2.28x | 2.50x (worse after shuffling) |
| assay + gemma3 4B (word) | urgency | `3` | 3.79x | 3.57x | 3.79x (worse after shuffling) |
| von 1.2 | command_safety | `risky` | 1.81x | 1.81x | 1.81x (about the same after shuffling) |
| von 1.2 | routing | `billing` | 1.76x | 1.76x | 1.76x (about the same after shuffling) |
| von 1.2 | urgency | `2` | 1.76x | 1.76x | 1.76x (about the same after shuffling) |
| openJev-verdict-2.0 | command_safety | `destructive` | 2.79x | 2.85x | 2.79x (better after shuffling) |
| openJev-verdict-2.0 | routing | `cancel` | 1.67x | 2.31x | 1.67x (better after shuffling) |
| openJev-verdict-2.0 | urgency | `5` | 3.88x | 3.88x | 3.88x (about the same after shuffling) |

## Full label bias, routing, shuffled condition

| System | billing | cancel | other | sales | technical |
|---|---|---|---|---|---|
| assay + gemma3 4B (letter) | 2.74x | 0.81x | 0.34x | 0.64x | 0.30x |
| assay + gemma3 4B (word) | 2.50x | 0.81x | 0.21x | 0.88x | 0.43x |
| von 1.2 | 1.76x | 1.71x | 0.50x | 0.40x | 0.54x |
| openJev-verdict-2.0 | 2.22x | 1.67x | 0.05x | 0.05x | 0.83x |

## Full label bias, urgency, shuffled condition

| System | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| assay + gemma3 4B (letter) | 1.26x | 0.24x | 1.71x | 1.10x | 0.90x |
| assay + gemma3 4B (word) | 0.32x | 0.79x | 3.79x | 1.12x | 0.85x |
| von 1.2 | 1.11x | 1.76x | 0.79x | 0.56x | 0.94x |
| openJev-verdict-2.0 | 0.00x | 0.00x | 0.00x | 0.00x | 3.88x |

`ratio` is predicted share ÷ true share. 1.0x is unbiased; every system above 1.5x on a task is shown. A ratio could not be computed where a system has no receipts for that task.

