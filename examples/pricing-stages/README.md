# Follow heuristic and exact pricing stages

In Coluna **0.8.2**, a pricing stage can span several master/pricing iterations. Once the default algorithm reaches exact pricing, finding another column keeps that stage. It does not restart the heuristic after each master solve.

This guide explains the configuration and trace in [this usage question](https://github.com/atoptima/Coluna.jl/issues/1145). It is an integration reference for an existing decomposition model, not a standalone vehicle-routing model.

## Match callback registration to solver IDs

Edit the existing `specify!` registration, retaining its multiplicities and any `branching_priority` option. The linked VRP registers the heuristic first and the exact callback second, with these model-specific bounds:

```julia
BD.specify!.(subproblems,
    lower_multiplicity = 1,
    upper_multiplicity = inst.numberOfVehicles,
    solver = [pricing_callback_heuristic, pricing_callback_exact])

colgen = Coluna.Algorithm.ColumnGeneration(
    stages_pricing_solver_ids = [2, 1])
```

Here `BD` means `BlockDecomposition`; `inst`, `subproblems` and both callbacks belong to the existing model. Use your own model's actual bounds and retain its other registration options. Do not add a separate solver-only `specify!` call: its [defaults overwrite multiplicities and branching priority](https://github.com/atoptima/BlockDecomposition.jl/blob/v1.15.1/src/formulations.jl#L105-L114). Pass this `colgen` object through your existing conquer/tree-search configuration, retaining the remaining algorithm options and callback implementations.

The entries in `stages_pricing_solver_ids` identify registered solvers. The default stage sequence traverses that list in reverse:

| Printed stage | Solver ID for this registration | Callback |
| --- | --- | --- |
| 2, initial | 1 | `pricing_callback_heuristic` |
| 1, exact | 2 | `pricing_callback_exact` |

Changing the callback registration order changes the IDs. Do not copy the same vector into a different registration without checking it. The [official solver-order documentation](https://github.com/atoptima/Coluna.jl/blob/v0.8.2/src/Algorithm/branchcutprice.jl#L36-L40) describes this reverse traversal; the [stage iterator](https://github.com/atoptima/Coluna.jl/blob/v0.8.2/src/Algorithm/colgen/default.jl#L315-L387) implements the mapping.

## Read the transition before changing the schedule

For the default context, [the transition rule](https://github.com/atoptima/Coluna.jl/blob/v0.8.2/src/Algorithm/colgen/default.jl#L380-L387) checks these conditions in order:

| Condition | Next stage |
| --- | --- |
| New master cuts were added | Return to the initial stage. |
| No columns were added and bounds have not converged | Move to a lower-numbered stage; after stage 1, end the stage sequence. |
| Otherwise | Keep the current stage. |

The requester [reported the fallback working](https://github.com/atoptima/Coluna.jl/issues/1145#issuecomment-6588520812). Their trace contains this transition:

| Iteration | Stage | Inserted columns |
| --- | --- | --- |
| 23 | 2, heuristic | 0 |
| 24 | 1, exact | 25 |

The exact callback then continuing at stage 1 is expected. New columns do not trigger a return to the heuristic. New master cuts are a separate reset condition, so this is not a claim that the heuristic can never run again within the same node.

The [stage definition](https://github.com/atoptima/Coluna.jl/blob/v0.8.2/docs/src/api/colgen.md#L235-L245) and [column-generation loop](https://github.com/atoptima/Coluna.jl/blob/v0.8.2/src/ColGen/ColGen.jl#L35-L86) explain why the list is not a fallback chain replayed after every master reoptimization. The [upstream stage tests](https://github.com/atoptima/Coluna.jl/blob/v0.8.2/test/unit/ColGen/colgen_stage.jl#L50-L103) include remaining at stage 1 after column insertion, terminal stage exhaustion and the new-cuts reset.

No option for a heuristic retry after every master reoptimization was found in the inspected [0.8.2 constructor](https://github.com/atoptima/Coluna.jl/blob/v0.8.2/src/Algorithm/colgen.jl#L68-L128). That would be a different scheduling policy. Repeated solver IDs alone do not establish such a policy.

## Keep the pricing-bound contract

A feasible heuristic solution cost is not, by itself, a proved lower bound for a minimization pricing problem. The [official staged-pricing GAP example](https://github.com/atoptima/Coluna.jl/blob/v0.8.2/test/e2e_extra/advanced_colgen/pricing_callback.jl) submits `-Inf` as the heuristic pricing dual bound and obtains its finite exact bound from an exact subproblem solve. Use the complete official example as a runnable reference within Coluna's test environment; its third-party solvers and test data are required.

For your own callbacks, verify the validity of every submitted bound against the actual pricing formulation and solver result. This guide does not certify a bound from omitted callback code or recommend changing it to an arbitrary finite value.

## Evidence and limits

The configuration, stage transitions and options above were checked against the linked 0.8.2 documentation and source, including the upstream test assertions. Those Julia tests were inspected, not executed here. The requester independently reported the initial heuristic-to-exact fallback working; their trace was not reproduced here.

The trace does not establish a globally optimal vehicle-routing solution, validate all callback bounds, demonstrate a performance improvement or verify a custom heuristic-after-every-iteration schedule. The demonstrated result is the initial fallback reaching exact pricing and inserting columns.

## Optional coffee

This guide is free. If it saves you time, buying me a coffee is entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
