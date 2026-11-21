# End-to-end example: three kinds of agent work, verified by hidden tests

A tiny Python package, `textkit`, has three independent pieces of work, one per
module. Each is a different kind of job an agent gets in practice:

| Task | Module | Kind of work |
|---|---|---|
| `ex1-w1-wrap` | `wrap.py` | **Implement from a spec.** A stub with a detailed docstring; public tests cover only the easy cases. |
| `ex1-w2-roman` | `roman.py` | **Add a strict API.** `from_roman` must accept every canonical numeral and reject `IIII`, `IC`, `VX`, ... |
| `ex1-w3-csvlite` | `csvlite.py` | **Bug hunt.** Public tests pass, but the parser breaks its spec in three ways. The agent has to find them by writing tests. |

Every agent also writes tests for its module. The coordinator then proves the
combined result in one command task that applies all three diffs and runs the
public tests, the agents' tests, and **hidden acceptance tests**
(`acceptance_test.py`) that no agent ever sees.

```
example/
  gateway.yaml        hero-demo-gw: agy install + Gemini, key injected outside the sandbox
  workspace.yaml      ex-textkit-ws: textkit + public tests, committed as a git repo
  acceptance_test.py  hidden tests; only the verify task runs them
  mkverify            builds the verify task from finished agent tasks' diffs
  tasks/ex1/          manifests from a real run (what members should write)
```

## 1. Prepare the cluster

```sh
ax ctx                                # expect ax-local (or the cluster you want)
ax apply -f example/gateway.yaml      # needs the hero-demo-gemini Secret; see the file's header
ax apply -f example/workspace.yaml    # waits for the pre-warm; re-applying is a no-op
ax describe workspace ex-textkit-ws   # Phase: Ready, SnapshotReady: True
```

## 2. Run the swarm

```sh
cd ~/ax-agy-swarm
agy
```

Then paste:

```
/swarm Run id ex1. Gateway hero-demo-gw and workspace ex-textkit-ws already
exist; the repo is /workspace/textkit (a git repo, test with `python3 -m unittest -v`).
1. Coordinator: run the baseline command task (expect 3 errors, all from wrap).
2. One worker each for wrap, roman and csvlite: an agent task as in
   example/tasks/ex1/ex1-w*-*.yaml. Agents must end their reply with the staged
   diff in a ```diff block.
3. Coordinator: once all three succeed, generate the verify task with
   `example/mkverify ex1 <the three task names> > tasks/ex1/ex1-coord-verify.yaml`,
   submit it, and wait. Done when it succeeds with every test OK.
Use example/tasks/ex1/ as the reference for the manifests.
```

## 3. What a run looks like

From the reference run on `ax-local` (JSON lines from `bin/axs`, trimmed):

```
PLAN    ex1-coord-baseline | ex1-w1-wrap, ex1-w2-roman, ex1-w3-csvlite (agent) | ex1-coord-verify
DONE    ex1-coord-baseline TASK_RESULT_FAILED  FAILED (errors=3)       <- expected: the wrap stub
STARTED ex1-w1-wrap / ex1-w2-roman / ex1-w3-csvlite                    <- in parallel
DONE    ex1-w2-roman  TASK_RESULT_SUCCEEDED  greedy parse + round-trip check, 2 new tests
FAILED  ex1-w1-wrap   dial tcp: lookup generativelanguage.googleapis.com: server misbehaving
FAILED  ex1-w3-csvlite  (same DNS error, retryable)
STARTED ex1-w1-wrap-retry1 / ex1-w3-csvlite-retry1                     <- retry with a new name
DONE    ex1-w1-wrap-retry1    TASK_RESULT_SUCCEEDED  paragraph-aware greedy wrap, 4 new tests
DONE    ex1-w3-csvlite-retry1 TASK_RESULT_SUCCEEDED  found: trailing empty field dropped,
                                                     "" escape ignored, unterminated quote accepted
STARTED ex1-coord-verify
DONE    ex1-coord-verify TASK_RESULT_SUCCEEDED  Ran 25 tests OK (8 hidden acceptance tests)
SUMMARY ...
```

The transient DNS failure was real. It shows why the protocol retries under a
new name: tasks are immutable, so you can't re-run a failed one.

## Things this example relies on

- **Every task gets its own copy of `/workspace`.** Changes made in one task
  are invisible to the others. Goals must be independent, and the only way to
  combine them is to carry the diffs into a new task, which is what `mkverify`
  does.
- **The agent's final reply is the task output.** `bin/axs result` shows it
  after the task finishes. `ax ssh` only works while a task is `Working`, so a
  report written to a file inside the sandbox can't be read afterwards. Ask
  for everything you need in the final reply.
- **Stage before diffing.** Agents add test files, and `git diff` doesn't show
  untracked files, so the goals ask for `git add -A && git diff --cached`. The
  workspace's `.gitignore` keeps `__pycache__` out of the diff.
- **Full output for diffs.** `bin/axs` trims output to its last 4000 characters,
  so `mkverify` reads the whole output with `ax get task`.
- **Warm starts.** Agent tasks use the same image and limits as the workspace;
  command tasks omit `spec.profile`. Both start from the snapshot in seconds.

## Run it without agy

```sh
bin/axs submit example/tasks/ex1/ex1-coord-baseline.yaml && bin/axs wait ex1-coord-baseline
bin/axs submit example/tasks/ex1/ex1-w{1-wrap,2-roman,3-csvlite}.yaml
bin/axs wait --timeout 1800 ex1-w1-wrap ex1-w2-roman ex1-w3-csvlite
example/mkverify ex1 ex1-w1-wrap ex1-w2-roman ex1-w3-csvlite > /tmp/ex1-coord-verify.yaml
bin/axs submit /tmp/ex1-coord-verify.yaml && bin/axs wait ex1-coord-verify
```

`tasks/ex1/ex1-coord-verify.yaml` is the verify task generated from the
reference run. It shows what one looks like and passes on its own.

## Clean up

Tasks are immutable, so delete them before you reuse the `ex1` names:

```sh
bin/axs ls ex1-                     # every task of the run
ax delete task <name>               # for each
ax delete workspace ex-textkit-ws   # optional
```
