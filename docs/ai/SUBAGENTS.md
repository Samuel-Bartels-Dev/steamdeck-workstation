# Agent collaboration and model selection

This is the shared collaboration policy for Codex and Claude Code. Read it with
[COMMON.md](COMMON.md). Keep tool entry points thin; do not duplicate this policy.

## When to delegate

For substantial tasks, delegate independent investigation, implementation or review
when parallel work will materially improve turnaround or confidence. Start with two
or three subagents, within the runner's limits. Keep small local fixes with the lead.
Do not launch every auditor for every task or create nested teams by default.
Use existing scripts for repeatable checks; agents interpret the results.

The lead owns requirements, task decomposition, interfaces, integration and the final
answer. Before spawning, assign each worker a bounded goal, relevant context, file
ownership, dependencies, acceptance criteria and expected evidence. Use the active
task document for durable decisions when one applies; avoid new planning artifacts
for trivial work.

## Models and roles

These are defaults, not claims that every model is available on every account.
Honor explicit user choices and runner restrictions. Custom Codex roles live in
`.codex/agents/`; they configure spawned agents, not the main session.

| Role | Default model / effort | Scope |
| --- | --- | --- |
| Lead (main session) | GPT-6.1 Sol / medium; high for complex integration | Plan, coordinate and integrate |
| `implementation_worker` | GPT-6.1 Sol / medium | Bounded module or installer implementation |
| `ui_worker` | GPT-6.1 Sol / high | Qt/QML UI and related Python state |
| `install_auditor` | GPT-6.1 Sol / high | Lifecycle, idempotence, logging and recovery review |
| `compatibility_auditor` | GPT-6.1 Sol / medium | SteamOS, Decky, storage and dependency evidence |
| `validation_auditor` | GPT-6.1 Sol / high | Final diff, safe tests and regression risks |
| `ui_auditor` | GPT-6.1 Sol / high | Navigation, layout and usability review |
| `deep_investigator` | GPT-6 Astra / high | Persistent or ambiguous failures across components |

Use Astra selectively when a reproduced failure survives a reasonable fix attempt,
evidence conflicts, or architecture needs deeper investigation. Do not escalate
every task automatically. For narrow read-only triage, the lead may request Luna
at high effort when supported; the explicit model in a custom role takes precedence
in Codex, so use a supported explicit spawn or built-in role for that override.

If a preferred model is unavailable, report the limitation and use an available
Sol model or inherit the current session, preserving the role's scope. Do not
retry unavailable models in loops or purchase API access. Claude Code follows
the same task division and uses its available models; OpenAI model IDs are not
Claude configuration.

## Ownership and communication

- Keep one writer per checkout. For parallel implementation, give workers separate
  Git worktrees and disjoint file ownership. If isolation is unavailable, serialize
  writes while investigations and reviews run in parallel.
- Agree shared interfaces before dependent implementation. Assign shared files to
  one owner; workers propose changes to that owner rather than overwriting them.
- Share discoveries, changed assumptions, interface changes and blockers promptly.
  Use runner-supported agent messages and follow-ups; include the lead on decisions.
  When direct peer messaging is unavailable, the lead relays concise handoffs.
- Ask a peer for a focused second opinion or reproduction when useful. Share paths,
  symbols, commands and evidence rather than whole logs or repeated repository scans.
- Stop dependent work on unresolved interface conflicts. The lead reconciles
  disagreements against code, reproduction and tests, then updates assignments.
- Workers return changes/findings, checks and outcomes, unresolved risks and the
  commit/worktree when applicable. Clearly distinguish observed facts from hypotheses.
- Reuse completed findings and checks. Retest after relevant changes, failures or
  unresolved concerns; do not repeat expensive suites just to keep agents busy.

## Integration and verification

The lead waits for required workers, reviews their combined diff, integrates in
dependency order and runs `./bin/deckctl repo validate` plus relevant tests.
Use an independent auditor for meaningful behavior changes where useful.
Read-only auditors must not install apps or perform provisioning; a test requiring
writes belongs with the lead or an authorized worker in an isolated environment.
Never treat source review or CI as proof of physical Deck behavior; report remaining
checks using [HARDWARE-TESTING.md](../HARDWARE-TESTING.md).

Example:

> Fix the Decky installer and its UI feedback. Have install_auditor trace lifecycle
> failures and ui_auditor inspect the UI in parallel. Agree the status interface,
> then assign implementation_worker and ui_worker separate worktrees and file
> ownership. Relay findings and blockers between them. Integrate their fixes,
> ask validation_auditor to review the final diff, and run the relevant safe checks.

## Runner setup

Current local Codex clients support project agent TOML files and
`.codex/config.toml`. This project caps spawned threads at three and defaults them
to Sol medium. Project config may require trusting the repository; older clients
may need an update. These files do not launch agents by themselves, grant tool
permissions, install models or change subscription limits.

Ask explicitly for delegation when the runner requires it; in Codex CLI use
`/agent` to inspect threads. ChatGPT Work can follow this policy when repository
context is loaded, but does not necessarily load local Codex configuration.
The policy requests delegation where useful; model routing and peer communication
still depend on the runner's supported tools.

Reference: [official Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).
