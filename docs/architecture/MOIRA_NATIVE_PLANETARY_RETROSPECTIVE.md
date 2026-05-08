# Moira Native Planetary Retrospective

**Status**: Retrospective
**Date**: 2026-05-08
**Companion documents**:
- [MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md](./MOIRA_NATIVE_PLANETARY_CLOSURE_TRACKER.md)
- [MOIRA_NATIVE_PLANETARY_CASH_IN_PLAN.md](./MOIRA_NATIVE_PLANETARY_CASH_IN_PLAN.md)
- [MOIRA_NATIVE_PLANETARY_PATH.md](./MOIRA_NATIVE_PLANETARY_PATH.md)
- [MOIRA_NATIVE_PERSISTENT_KERNEL_STORE.md](./MOIRA_NATIVE_PERSISTENT_KERNEL_STORE.md)

---

## 1. Purpose

This document answers one narrow question:

What did the native planetary closure effort actually gain us?

It is not a roadmap.

It is not a claim that full native closure has already been achieved.

It is a truthful accounting of what changed, what improved, and what did not.

---

## 2. The Short Answer

The native planetary effort produced real gains, but mostly at the substrate and integration level rather than as a dramatic public-product speed breakthrough.

What is now true:

- the native reader and evaluator substrate is materially real
- the canonical planetary path is more integrated with that substrate than before
- the repository now knows which optimization directions are worth pursuing and which are not

What is not yet true:

- a large, stable public `planet_at(...)` speedup
- a large, stable public `all_planets_at(...)` speedup

So the effort was not wasted.

But its gains were architectural and foundational more than spectacular at the user-facing benchmark layer.

---

## 3. What We Gained

### 3.1 A real native planetary substrate

Before this work, the native story could still be read as partial or experimental.

After this work, the substrate is clearly real:

- native SPK summary scanning exists
- native segment payload handling exists
- native Chebyshev evaluation exists
- native evaluator reuse exists
- persistent native kernel ownership exists

This means the C++ layer is no longer merely an extension surface with weak engine contact.

It is part of the actual planetary machinery.

### 3.2 A clearer native/Python boundary

The effort forced the repository to identify where native help actually begins and where Python still governs:

- native below the reader boundary
- Python above that boundary for the canonical planetary manuscript

That boundary is now far less vague.

This is a real gain because future work no longer has to guess where the remaining cost lives.

### 3.3 Better reader and evaluator ownership

The persistent kernel-handle work was valuable even when it did not explode the public benchmarks.

It gave us:

- longer-lived native ownership
- evaluator reuse
- less accidental reconstruction
- a cleaner substrate for any future higher-level route

This is the kind of gain that makes later work disciplined rather than improvised.

### 3.4 Shared orchestration closure in the planetary path

`PP-08` and `PP-09` are no longer just conceptual rows in a tracker.

They now correspond to real code-level changes:

- shared vector-cache routing
- shared Earth-state handling
- cleaner multi-body orchestration
- one admitted internal planetary core

That is not merely aesthetic.

It means the planetary engine has been structurally tightened around a real substrate.

### 3.5 Benchmark truth instead of benchmark mythology

One of the most important gains was negative knowledge.

We now know, from actual runs, that:

- some reader-level wins are real
- some public-path optimizations cash out only weakly
- some seemingly plausible optimizations regress

This matters because it prevents the project from telling itself a false performance story.

The closure effort replaced assumption with measurement.

---

## 4. What We Did Not Gain

### 4.1 No large public planetary speed breakthrough

The public artifacts did not turn into a strong native victory.

`planet_at(...)` and `all_planets_at(...)` remained:

- near parity
- slightly positive on some runs
- slightly negative on others

That is a real limitation.

The native substrate is stronger than the public benchmark story above it.

### 4.2 No easy cash-in path after the first structural wins

The repository tested multiple conversion ideas.

The outcome was:

- `CI-1`: structurally correct, but no meaningful cash-in
- `CI-2`: modestly useful, the best public-path conversion step
- `CI-3`: regression, rejected
- `CI-4`: regression, rejected

So the easy nearby optimizations have largely been exhausted.

### 4.3 No evidence that parity-preserving readability can yield much more incremental gain

This is a major conclusion.

The current architecture appears to be near the ceiling of what it can produce while all of these remain true:

- Python owns the canonical manuscript
- parity to current semantics is strict
- readability and inspectability remain first-class

That is not failure.

But it is a real design limit.

---

## 5. What We Learned

### 5.1 The native work was worth doing

The effort was worth doing because it converted uncertainty into knowledge:

- which layers matter
- where the cost moved after substrate improvements
- which routes are dead ends

The project now has a much stronger basis for deciding whether a larger redesign is justified.

### 5.2 The remaining bottleneck is higher in the stack

The problem is no longer mainly:

- raw segment math
- evaluator reuse
- first-order reader access

The remaining pressure is now more about:

- public-path orchestration
- policy-preserving correction work
- Python-owned canonical manuscript cost

### 5.3 Future gains will require a different kind of move

If the repository wants materially more speed while preserving truth, the next gain probably will not come from more local tuning.

It would need one of these:

- a higher native boundary
- a different public/native execution split
- or acceptance that the current architecture is already close to its practical ceiling

---

## 6. Final Reading

The native planetary effort achieved three lasting things:

1. it made the native substrate real and integrated
2. it tightened the Python planetary path around that substrate
3. it established the actual ceiling of the current parity-preserving architecture

So the correct retrospective is not:

- "the optimization failed"

It is:

- "the substrate succeeded"
- "the public cash-in was modest"
- "the architecture's current limit is now visible"

That is a meaningful gain in its own right, because it tells the truth about where Moira stands.
