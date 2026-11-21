---
name: ax
description: Create, run, monitor, and clean up AX tasks (sandboxed agent/command workloads) with the `ax` CLI and the `bin/axs` helper. Use whenever a swarm member needs to launch work on the AX cluster or check on it.
---

# Driving AX from a swarm member

AX runs each unit of work as a `Task` in an isolated sandbox on the cluster of
the current kube context (`ax ctx` shows it; `ax-local` is the local Kind
cluster). Full docs: `~/ax/README.md`, `~/ax/docs/manifests.md`,
`~/ax/docs/concepts.md`.

## Resources

| Kind | Role | Mutable? |
|---|---|---|
| `Workspace` | Repos/files/setup commands materialized at `/workspace`, pre-warmed into a snapshot | **No**: make a new name (`foo-ws-v2`) to change |
| `Gateway` | Egress allowlist + credential injection; no gateway = no network | Tasks copy rules at creation |
| `Task` | Image + command (or agent goal) + bindings | **No**: spec is immutable, create a new task |
| `Model` | Model provider config for AX itself | |

List a `Workspace`/`Gateway` before the `Task` that binds it (same file or
earlier apply). Images must be pinned by digest (`@sha256:`); a tag-only image
fails with `TemplateCreationFailed`.

## Lifecycle

`ax apply` creates tasks **Suspended**. `ax resume task <name>` starts them.
States: `TASK_STATE_QUEUED → WORKING → COMPLETED | FAILED | CANCELLED`, plus
`SUSPENDED`, `SUSPENDING`, `REQUIRES_ACTION`, `IDLE`. Results live in
`status.outcome` (`result`, `exitCode`, `output` = tail of the command's stdout).
A completed task cannot be resumed again; to re-run, create a new task.

## The helper: `bin/axs` (prefer it — JSON-lines output)

```bash
bin/axs submit tasks/<run>/foo.yaml          # ax apply + ax resume every Task in the file
bin/axs wait --timeout 1800 <task> [<task>]  # block until terminal/stuck; exit 0 only if all succeeded
bin/axs result <task>                        # current state/result/output, no waiting
bin/axs ls <run>-                            # every task of a run
```

## Raw CLI

```bash
ax apply -f file.yaml                 # multi-doc; Workspace apply waits for pre-warm (up to 5m)
ax resume task NAME | ax suspend task NAME
ax get tasks | ax get task NAME       # task = full YAML incl. status
ax describe task NAME                 # human readable, includes Output and Conditions
ax ssh NAME -- cat /workspace/reports/x.md   # needs spec.debug: true and a running task
ax delete task NAME                   # blocks until the sandbox is gone
ax get workspaces | ax get gateways   # discover what can be bound
```

There is no `-o json` and no label filter; use `bin/axs` or parse the YAML.

## Writing a task

Start from `templates/command-task.yaml` (deterministic command) or
`templates/agent-task.yaml` (Antigravity agent driven by `spec.goal.text`).
Save to `tasks/<run>/<task-name>.yaml` so there is an audit trail.

- Name: `<run>-<worker>-<slug>`, lowercase, `[a-z0-9-]`, ≤ 63 chars.
- Reuse an existing Ready workspace when possible (`ax get workspaces`); omit
  `spec.profile` (or match the workspace's profile exactly) to start warm.
- Need a new environment? Write a new `Workspace` with `spec.profile` and
  `spec.setup` (`git`, `files`, `commands`), name it `<run>-ws-<slug>`.
- Keep the whole task < 31 KiB; never put secrets in `spec.config`/`env`
  values — use a Gateway `replaceHeaders` credential instead.
- Agent goals must be self-contained: the sandboxed agent cannot see the
  board. Tell it where to write its report and read it back with `ax ssh`.

## Failure triage

| Symptom | Cause / fix |
|---|---|
| `no free workers available` on resume | No WorkerPool capacity. Wait and retry, or tell the coordinator to lower concurrency. |
| `TemplateCreationFailed` | Image not pinned by digest or bad limits. |
| `GatewayBindingFailed` | Substrate rejected a gateway rule. |
| `FailedPrecondition` on apply | Bound workspace/gateway missing, or you modified an immutable Workspace. |
| Resume CLI times out | First workspace init is slow; task keeps starting. Poll with `bin/axs wait`. |
| Task FAILED | Read `bin/axs result`; for more, `ax describe task`, then `ax ssh` if still up. |
