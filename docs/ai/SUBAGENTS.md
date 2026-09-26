# Codex subagents

Codex reads `AGENTS.md` for repository policy. The TOML files in `.codex/agents/` define optional, project-scoped roles in local Codex clients. The built-in `worker` can implement changes; the lead agent owns integration and the final answer. These files do not launch agents or install another AI runtime.

| Role | Use when | Return |
| --- | --- | --- |
| `install_auditor` | Installer, module lifecycle, recovery or logs change | Idempotence, failure and SteamOS risks |
| `compatibility_auditor` | Decky, SteamOS, hardware, dependencies or downloads change | Supported/unknown combinations and evidence |
| `validation_auditor` | A change spans modules or a release is being prepared | Safe checks run, gaps and regression risks |
| `ui_auditor` | Qt/QML setup or option flow changes | Navigation, layout and usability findings |

Ask for only the roles that have independent work. Example:

> Review the Decky installer change. Delegate the install path to `install_auditor` and SteamOS/plugin evidence to `compatibility_auditor` in parallel. Wait for both, then implement the fix as the sole writer. Ask `validation_auditor` to check the final diff and safe tests. Report remaining hardware checks separately.

For a small, local edit, use the lead agent alone. Keep a single writer per checkout; use separate Git worktrees if multiple agents must implement independent changes. Give each agent a bounded question, paths, expected output and whether it may edit. Run `./bin/deckctl repo validate` and relevant tests after integration. A read-only auditor cannot prove behavior on a physical Deck; use `docs/HARDWARE-TESTING.md` for that gate.

To choose roles in another repository, first map its entry points, risky boundaries, tests and CI. Add a role only when a recurring task benefits from a distinct scope, evidence source or tool permission. Prefer two focused reviewers over a permanent agent for every directory. Reassess after architecture or release workflow changes; a full review on every task is unnecessary.

In Codex CLI, ask explicitly for delegation and use `/agent` to inspect threads. Current Codex releases support project roles under `.codex/agents/`; the availability of subagent controls depends on the client and account. This setup uses the existing Codex session, not the separately billed Agents API.
