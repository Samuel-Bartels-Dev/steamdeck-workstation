# AI Workflow

Recommended loop:

1. Human/ChatGPT defines architecture, acceptance criteria, and task scope.
2. Create a task using `deckctl ai task <module> "description"` or the template.
3. Coding agent reads root instructions + target module context only.
4. Agent implements, runs relevant tests and `deckctl repo validate`.
5. Human/ChatGPT reviews diff and behavior.
6. Merge/release only after verification.

This keeps Codex/Claude context focused and reduces repeated repository discovery.
