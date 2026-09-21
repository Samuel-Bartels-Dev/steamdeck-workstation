# v0.2.36 — Clearer setup flow

Category cards browse individual options without selecting a bundle. Fresh setups start with no optional selections; existing saved plans are restored. Checkboxes select installs, while Decky Loader and CSS Loader expose their own dependent choices.

Search within categories, return using the breadcrumb, and review actual selected items with Edit links. Decky and CSS choices stay together. Full-preset and clear-all actions confirm before replacing choices. Saving freezes controls until the result returns.

The installation screen uses readable states, reports nonzero operation exits, and leads from installation into guided setup and sign-in. The UI runs only while open; vendor prompts remain in Konsole.

Validation includes native Qt flow checks at 1120×720 and 800×600, proving browsing does not change selections, single-tool choices stay independent, search and review reflect the plan, and failure states are not presented as success.
