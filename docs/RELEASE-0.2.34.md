# v0.2.34 — Choose your workstation setup

A native Qt Quick setup app replaces sequential checkbox dialogs. Its persistent
stage navigation, spacious feature cards, optional app choices, review screen and
installation results fit the Steam Deck display. Start small or select the full
workstation, then adjust individual choices before saving or installing.

The UI uses SteamOS's existing Qt Quick runtime. It runs only on demand and closes
its temporary loopback connection when the window exits. Vendor installers retain
Konsole for interactive prompts. Sign-in/pairing and optional Docker have separate
actions. Terminal-only environments retain a text selection flow.

Base support and selected app dependencies are included automatically. Unselected
features do not block setup readiness. Saving a plan preserves existing apps and
data; installation requires the explicit Save & install action.

See the [setup builder guide](../README.md#choose-only-the-stages-you-want).

- Individual launcher/tool and Decky plugin choices, including clear-all. Saved choices govern provisioning and guided setup; explicit plugin opt-outs survive future manifest updates.
