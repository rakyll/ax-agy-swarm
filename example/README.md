# End-to-end example: fix three bugs with a swarm

A tiny Python package, `textkit`, ships with three independent bugs, one per
module, and a unittest suite that catches them (5 of 7 tests fail). The swarm
splits the fix across three Antigravity agent tasks, then proves the combined
result in one command task.

```
example/
  workspace.yaml   ex-textkit-ws: textkit + tests, committed as a git repo
  tasks/ex1/       reference manifests from a real run (what members should write)
```

## 1. Prepare the cluster

```sh
ax ctx                                # expect ax-local (or the cluster you want)
ax get gateways | grep hero-demo-gw   # agent tasks reach Gemini through it
ax apply -f example/workspace.yaml    # waits for the pre-warm; re-applying is a no-op
ax describe workspace ex-textkit-ws   # Phase: Ready, SnapshotReady: True
```

If `hero-demo-gw` is missing, set it up from `~/ax/hack/hero-demo/gateway.yaml`
(it needs the `hero-demo-gemini` Secret described there).

## 2. Run the swarm

```sh
cd ~/ax-agy-swarm
agy
```

Then paste:

```
/swarm Run id ex1. Workspace ex-textkit-ws already exists; the repo is
/workspace/textkit (a git repo, run tests with `python3 -m unittest -v`).
1. Coordinator: run a baseline command task that runs the whole suite (expect 5 failures).
2. One worker per module (slug, words, roman): an agent task that fixes only
   textkit/<module>.py, runs tests.test_<module>, and ends its final reply with
   `git -C /workspace/textkit diff` in a ```diff block.
3. Coordinator: a verify command task that `git apply`s all three diffs and runs
   the whole suite. Done when it succeeds with 7 tests OK.
Use example/tasks/ex1/ as the reference for the manifests.
```

## 3. What a run looks like

The board should go roughly like this (the JSON lines come from `bin/axs`):

```
PLAN    ex1-coord-baseline (command) | ex1-w1-slug, ex1-w2-words, ex1-w3-roman (agent) | ex1-coord-verify (command)
STARTED ex1-coord-baseline
DONE    ex1-coord-baseline TASK_RESULT_FAILED  FAILED (failures=5)   <- expected
STARTED ex1-w1-slug / ex1-w2-words / ex1-w3-roman                    <- in parallel
DONE    ex1-w1-slug  TASK_RESULT_SUCCEEDED  missing .lower()
DONE    ex1-w2-words TASK_RESULT_SUCCEEDED  split(" ") -> split()
DONE    ex1-w3-roman TASK_RESULT_SUCCEEDED  added CM, CD, XC, XL, IX, IV
STARTED ex1-coord-verify
DONE    ex1-coord-verify TASK_RESULT_SUCCEEDED  3 files changed; Ran 7 tests OK
SUMMARY ...
```

On `ax-local` the whole run took a few minutes: the command tasks finish in
seconds and the agent tasks in about a minute each.

## Things this example relies on

- **Every task gets its own copy of `/workspace`.** Fixes made in one task are
  invisible to the others, so goals must be independent, and the only way to
  combine them is to carry the diffs into a new task (`ex1-coord-verify.yaml`
  inlines them in a `git apply` heredoc).
- **The agent's final reply is the task output.** `bin/axs result` shows it
  after the task finishes. `ax ssh` only works while a task is `Working`, so a
  report written to a file inside the sandbox cannot be read afterwards; ask
  for everything you need in the final reply.
- **Warm starts.** Agent tasks use the same image and limits as the workspace;
  command tasks omit `spec.profile`. Both start from the snapshot in seconds.

## Run it without agy

The reference manifests work on their own:

```sh
bin/axs submit example/tasks/ex1/ex1-coord-baseline.yaml && bin/axs wait ex1-coord-baseline
bin/axs submit example/tasks/ex1/ex1-w{1-slug,2-words,3-roman}.yaml
bin/axs wait --timeout 1200 ex1-w1-slug ex1-w2-words ex1-w3-roman
bin/axs submit example/tasks/ex1/ex1-coord-verify.yaml && bin/axs wait ex1-coord-verify
```

The verify manifest has the diffs from the reference run baked in. On a fresh
run, rebuild its heredoc from the new agent outputs.

## Clean up

Tasks are immutable, so delete them before you reuse the `ex1` names:

```sh
for t in ex1-coord-baseline ex1-w1-slug ex1-w2-words ex1-w3-roman ex1-coord-verify; do ax delete task $t; done
ax delete workspace ex-textkit-ws   # optional
```
