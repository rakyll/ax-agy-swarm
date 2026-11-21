# AX swarm workspace

This directory is where an Antigravity swarm (`agy`, then `/swarm <task>`)
coordinates work that runs as **AX tasks** on a cluster. Swarm members plan,
launch, watch, and verify; the heavy lifting runs inside AX sandboxes.

Load the `ax` skill (`.agents/skills/ax/SKILL.md`) before touching the cluster.

## Layout

```
bin/axs       JSON-lines helper over the ax CLI: submit, wait, result, ls
templates/    command-task.yaml (deterministic command), agent-task.yaml (Antigravity agent goal)
tasks/<run>/  every manifest a member submitted, one file per task (audit trail)
```

## Roles

**Coordinator**
1. Pick a short run id `<run>` (e.g. `r1`, `fixtests3`), lowercase `[a-z0-9]`. Post it first.
2. Check the cluster: `ax ctx`, `ax get workspaces`, `ax get gateways`, `bin/axs ls`.
   If the context is not the one the user intends, stop and ask.
3. Split the goal into independent AX tasks. Post a plan: one line per task
   with name, owner, kind (command/agent), workspace, and done criteria.
4. Assign each task to exactly one worker. Keep at most **8 AX tasks running**
   at once unless the user says otherwise (local clusters have few workers).
5. When all workers report, verify results yourself (`bin/axs result`) and
   write the final summary.

**Workers**
1. Own only the tasks assigned to you. Never resume, suspend, or delete a
   task another member owns; ask on the board instead.
2. For each task: write `tasks/<run>/<name>.yaml` from a template,
   `bin/axs submit` it, post `started <name>`, then `bin/axs wait <name>`.
3. Post the JSON line from `wait` (trim long output) and your judgement of
   whether the done criteria are met. For agent tasks, read the report with
   `ax ssh <name> -- cat /workspace/reports/<slug>.md` and check the diff with
   `ax ssh <name> -- git -C /workspace/<repo> diff --stat`.
4. On failure, triage with the skill's table, retry at most twice with a new
   name (`...-retry1`), then escalate to the coordinator.

## Board protocol

Prefix posts so the feed stays scannable:
`PLAN`, `CLAIM <task>`, `STARTED <task>`, `DONE <task> <result>`,
`FAILED <task> <reason>`, `BLOCKED <reason>`, `SUMMARY`.

## Hard rules

- Never `ax delete` workspaces or gateways you did not create in this run, and
  never touch tasks outside your run's `<run>-` prefix.
- Never `ax install`, `ax uninstall`, `ax local delete`, or switch `ax ctx`
  without the user's explicit instruction.
- Never put credentials in manifests; use gateways that already inject them.
- Clean up at the end only if the user asked: `ax delete task <name>` for the
  run's tasks (keep the manifests in `tasks/`).
