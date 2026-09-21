# On-demand AI coding workspace

Use `deckctl setup customize` to choose individual tools in this category. Selections are saved in `~/.config/deckctl/components.json` and govern installation, verification, and guided setup. Deselecting a tool preserves existing installations and personal settings. Older setups without saved component choices retain their previous defaults.

Owned by `lib/deckctl/ai_workspace.py`. Enabled in the normal module plan after
Terminal, which provides the required OpenCode client. Ghostty, tmux and Neovim
are optional. Ollama and model download have separate selectors; selecting the
model includes its required Ollama engine. A cloud-only setup can omit both. Installation downloads
Ollama's official Linux archive, verifies its GitHub SHA-256 digest, and copies the
raw executable to `~/.local/bin/ollama`. Bundled libraries stay under
`~/.local/share/deckctl/ollama/`, linked through `~/.local/lib/ollama`. No sudo,
pacman, service, login hook or daemon autostart is installed. Existing untracked
binaries/libraries are preserved and reported instead of overwritten.

The upstream archive is currently large because it bundles runtime libraries;
allow at least 8 GiB free for staging and the model. `zstd` is required. An
interrupted runtime promotion can leave retained files that require inspection
before retrying; no automatic deletion of unknown runtime trees is performed.

Installation starts a temporary, owned loopback engine and automatically pulls
`qwen2.5-coder:1.5b`. It stops that engine and its runners after download, including
failure. Model files remain on disk at `~/.local/share/deckctl/ollama/models`.
Presence verification checks manifest/blob sizes, not model inference quality.

## Use

```bash
deckctl terminal apply             # install terminal/editor tools
deckctl ai-workspace install       # configure, install Ollama, pre-pull model
deckctl ai-workspace open          # foreground local OpenCode session
deckctl ai-workspace status --json
```

In Ghostty, run the same commands. `tm`, `nvim` and `opencode` remain ordinary
commands. tmux is not auto-started: detaching a persistent tmux client is NOT exiting
the workspace, and its server remains alive until you exit the OpenCode session.
For close-window-to-stop behavior, launch the workspace directly in Ghostty.

## Profiles and authentication

The local launch profile is `local-ollama`. OpenCode uses a registered provider
with that name, `http://127.0.0.1:11435/v1`, and a conservative `local-coder` chat
agent with tools disabled. The requested 1.5B model is suitable for lightweight
coding assistance; full autonomous editing/tool reliability has not been verified.

The cloud launch profile is `chatgpt-pro`. It uses OpenCode's built-in `openai`
provider and supported browser sign-in. It does not start Ollama.

1. Run `opencode`, enter `/connect`, choose **OpenAI**, then **ChatGPT Plus/Pro**
   and finish browser sign-in.
2. Run `opencode models openai` and choose an available model for your account.
3. Run `deckctl ai-workspace open --profile chatgpt-pro --model openai/MODEL_FROM_LIST`.

This implementation does not invent an `openai-web-session` provider or ask users
to copy a ChatGPT web access token. OpenCode handles OAuth credentials separately.
Account access, subscription limits and available models depend on the provider.

Configuration is merged into `~/.config/opencode/config.json`, preserving unrelated
keys. Conflicting reserved values cause a clear error without modifying the file.
The wrapper uses `OPENCODE_CONFIG` to load that requested filename explicitly;
it also supplies reserved provider/agent values as inline configuration so a
project file cannot redirect the owned local endpoint. Existing OpenCode global
and project settings otherwise retain their normal precedence.

## Gaming and process lifetime

`OLLAMA_KEEP_ALIVE=0` is forced for the owned server. It requests model unload after
each response; it does not promise microsecond timing or a model-free idle server.
Closing the workspace terminates its server process group, including model runners.
Normal exit, client failure, SIGINT, SIGTERM and SIGHUP have cleanup paths. A
busy endpoint or concurrent workspace is refused; unrelated servers are never
borrowed, killed by name, or claimed as owned.

This removes the workspace's running AI processes after normal/handled exits. It
does not claim 100% system resources, purge the OS page cache, stop unrelated apps,
or guarantee cleanup after SIGKILL, a kernel crash, or a session deliberately left
running in tmux. `status` reports endpoint occupancy, not a RAM/VRAM measurement or
ownership proof. Inspect unexpected occupancy before gaming; do not kill unknown
processes automatically. Request-level Ollama keep_alive values can override the
server default; the supplied OpenAI-compatible configuration does not set them.

## Sources and validation

- [Ollama manual Linux distribution](https://docs.ollama.com/linux#manual-install)
- [Ollama model lifetime](https://docs.ollama.com/faq)
- [OpenCode local/OpenAI providers](https://dev.opencode.ai/docs/providers/)
- [OpenCode custom configuration path](https://dev.opencode.ai/docs/config/)

Tests use fake engines and actual temporary process groups/loopback HTTP. They
cover failed pulls, client failures, concurrent workspaces, busy ports, SIGTERM,
config preservation and archive traversal. They do not download a real model or
certify Steam Deck GPU inference, real account sign-in or Ghostty rendering.
