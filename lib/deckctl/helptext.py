"""Command reference shared by argparse, the Markdown guide, and the man page.

Every leaf has an explicit operational description. Parser traversal is also used
by tests so newly registered commands cannot silently ship without documentation.
"""
from __future__ import annotations
import argparse

# Description | effects and expected outcome | example arguments (without deckctl).
PAGES = {
'detect': ('Identify Steam Deck model, SteamOS, and battery health from local system files.', 'Read-only. Unknown hardware remains unknown; no model is guessed.', 'detect'),
'plan': ('List enabled modules in dependency order with their current readiness.', 'Read-only. Runs module verifiers; does not provision anything.', 'plan'),
 'apply': ('Provision enabled modules, recording progress for repeatable retries.', 'Within the same release, skips previously ready modules only if a fresh verifier still confirms readiness. New releases rerun module reconciliation. Records interruptions before execution and failures after execution; continues other modules. Account/vendor configuration may require setup run.', 'apply'),
'verify': ('Run enabled module verifiers and report readiness, including hardware context in JSON mode.', 'Read-only. Exit 0: ready/optional; 1: failed or absent; 2: degraded or user configuration required. A verifier timeout is FAILED.', 'verify --json'),
'doctor': ('Run repair actions for one module, or all enabled modules that are not READY.', 'May install packages, rewrite managed configuration, or launch vendor repair. Rechecks readiness afterward using the same exit statuses as verify.', 'doctor decky'),
'inventory': ('Report the release version, hardware, module readiness, and storage.', 'Read-only. Output may contain private host addresses and paths; use support-bundle for sharing.', 'inventory --json'),
'support-bundle': ('Create a sanitized diagnostic ZIP from an explicit set of project status and configuration data.', 'Writes ~/DeckSupportBundles. Excludes credential stores, keys, passwords, ROMs, BIOS, saves, and arbitrary logs/files. Inspect before sharing.', 'support-bundle'),
'post-update': ('Reapply user-space integration after a SteamOS update and inspect essential services.', 'Restages Decky setup and repairs terminal configuration, selected Decky plugins/CSS, and controller templates. Vendor authentication may remain required.', 'post-update'),
'ui safe': ('Capture CSS profiles and enter a recoverable UI safe mode.', 'Moves active CSS profiles out of service and records restoration state. --minimal also stops Decky’s plugin service; may request sudo.', 'ui safe --minimal'),
'ui restore': ('Restore UI state captured by ui safe.', 'Restores saved profile locations and restarts the plugin service when needed. No-op guidance is printed when no safe-mode snapshot exists.', 'ui restore'),
'storage health': ('Inspect block devices, mount points, free space, and configured storage roles.', 'Read-only. Uses lsblk; does not format, mount, or move data.', 'storage health --json'),
'storage recommend': ('Recommend a storage role using game hints or an explicit emulation system.', 'Read-only advice. No game files are moved.', 'storage recommend "World of Warcraft"'),
'storage migration-status': ('Inspect internal and removable Emulation directory locations and migration prerequisites.', 'Read-only. Use this before migrating or finalizing a migration.', 'storage migration-status'),
'storage migrate-emulation': ('Stage a migration guide and launch EmuDeck’s supported migration workflow.', 'Records migration intent and opens EmuDeck when available. EmuDeck performs the migration; the original tree must be retained until you verify games and saves.', 'storage migrate-emulation'),
 'storage finalize-emulation-migration': ('Verify migrated content and switch the internal Emulation path to the card.', 'Compares every preserved source entry with SHA-256 before changing paths. --yes renames the original to a rollback directory and creates an Emulation symlink to the verified card. Never deletes original data. Existing correct vendor migration links remain unchanged; mismatched links fail. Close emulators first.', 'storage finalize-emulation-migration --yes'),
'game register': ('Record a locally installed game, its launcher, location, and storage role.', 'Updates the game registry; does not download or install the game. Quote names and paths containing spaces.', 'game register "Example Game" --launcher steam --path ~/Games/example --storage-role internal'),
'game ready': ('Check a registered game’s location and readiness requirements.', 'Read-only. Returns a nonzero status when requirements are missing.', 'game ready "Example Game"'),
'game doctor': ('Explain readiness problems for a registered game with additional diagnostics.', 'Inspects the registered path and launcher information; follow the reported corrective guidance.', 'game doctor "Example Game"'),
'remote register': ('Register a Sunshine host reachable by hostname, IP, or Tailscale address.', 'Writes hosts.json. Optional MAC enables Wake-on-LAN; relay is an SSH user@host on the host’s local network. Port must be 1..65535.', 'remote register desktop --target desktop --mac AA:BB:CC:DD:EE:FF'),
'remote test': ('Probe a registered host’s Sunshine TCP port and available Tailscale connectivity.', 'Network diagnostics only. A TCP response does not prove pairing or successful video streaming; inspect each result.', 'remote test desktop'),
'remote wake': ('Send a Wake-on-LAN magic packet directly or through the configured SSH relay.', 'Sends a broadcast packet. Requires a registered MAC and host firmware/NIC support; sending the packet does not prove the host woke.', 'remote wake desktop'),
'remote wait': ('Poll a registered Sunshine host until its port is reachable or the timeout expires.', 'Network probes only. Returns 0 on reachability and nonzero on timeout. Does not launch a stream.', 'remote wait desktop --timeout 90'),
'remote host-kit': ('Package the Windows Sunshine host setup scripts and selected registered host metadata.', 'Writes a ZIP in ~/DeckExports or --out. Does not execute Windows code on the Deck. Host names must be safe filename components.', 'remote host-kit desktop --out ~/DeckExports'),
'backup saves': ('Archive discovered emulator saves, WoW configuration, and project configuration with a restore manifest.', 'Writes the configured backup destination. Contains private saves/configuration: keep it private and verify the manifest. It is not a sanitized support bundle.', 'backup saves'),
 'restore': ('Preview, select, restore and verify categories from a v2 save/settings backup.', '--dry-run validates paths, categories and free space without restoring. --category NAME is repeatable; --yes accepts selection without a dialog. Previous content is retained under state/restore-rollback; writes are atomic per file and SHA-256 checked afterward. A failed run retains its rollback and journal. This restores personal data, not app binaries or login sessions; run apply/setup afterward as needed.', 'restore ~/DeckBackups/backup.tar.gz --dry-run'),
'travel check': ('Check readiness for offline travel, including module readiness and reminders about backup and remote checks.', 'Read-only. A passing check cannot validate every game’s offline license; launch your games offline before leaving.', 'travel check'),
'travel lock': ('Enable the project travel-mode setting.', 'Writes a travel-lock record. This does not switch off radios or guarantee offline game licensing.', 'travel lock'),
'travel unlock': ('Disable the project travel-mode setting.', 'Removes the travel-lock record. This does not change network interfaces.', 'travel unlock'),
'ai context': ('Print the engineering context and module documentation used for an AI-assisted task.', 'Read-only. MODULE must identify a registered module.', 'ai context decky'),
'ai task': ('Create a local task document for a module and supplied description.', 'Writes a task file in tasks/active in the repository. Does not contact an AI service or send project data.', 'ai task decky "Inspect plugin readiness"'),
'repo validate': ('Run repository contracts, syntax checks, feature guards, and behavioral regression tests.', 'Runs offline tests in isolated temporary homes. Python compilation may create build caches. Returns nonzero for any failing gate; does not install vendor applications.', 'repo validate'),
'profile list': ('List bundled hardware/behavior profiles.', 'Read-only. These are deckctl profiles, separate from CSS Loader profiles.', 'profile list'),
'profile show': ('Display the requested bundled deckctl profile.', 'Read-only. Prints the profile’s configuration so it can be reviewed before applying.', 'profile show oled'),
'profile apply': ('Select a bundled deckctl hardware/behavior profile.', 'Writes the active profile setting. Does not independently reinstall all modules.', 'profile apply oled'),
'profile auto': ('Select the bundled profile matching detected Deck hardware.', 'Writes the profile selection when hardware can be identified; unknown hardware needs an explicit selection.', 'profile auto'),
'profile export': ('Package portable desired state, captured CSS profiles, and controller layouts.', 'Writes a sanitized profile ZIP; captures live CSS profiles first. Only approved configuration formats are exported. Browser/Keeper credentials and arbitrary folders are excluded.', 'profile export --out ~/DeckExports/my-profile.zip'),
'profile import': ('Validate and import a portable desired-state ZIP.', 'Copies approved configuration files after preflight and saves previous files under state/profile-import-rollback. Apply the reported component commands afterward; import does not run bundled scripts.', 'profile import ~/DeckExports/my-profile.zip'),
'launcher status': ('Inspect launcher prerequisites and known game-launcher installations.', 'Read-only. Installed launchers may still need an account login.', 'launcher status'),
'launcher install': ('Launch the established Battle.net installation workflow.', 'Installs/configures the Battle.net launcher through the project’s existing user-space path. Blizzard login, game ownership, and downloads require user interaction.', 'launcher install battlenet'),
'channel': ('Show or select the release channel: stable, beta, or dev.', 'Without NAME, read-only. With NAME, saves the selection for future update checks; does not install a release.', 'channel stable'),
'update check': ('Query the configured release source and display the installed and available versions.', 'Read-only except network access. With no configured source, explains how to use a local archive.', 'update check'),
'update apply': ('Validate and install a new persistent control-plane release.', 'Uses --archive locally or downloads a release with checksum verification. Runs repository tests before installation and records rollback history. Removes its own unchanged downloaded tarball after successful promotion; keeps explicitly supplied archives and prior releases. Local archives must be trusted executable code.', 'update apply --archive ~/Downloads/steamdeck-workstation-v0.2.26.tar.gz'),
'update rollback': ('Select an available previous persistent release and reactivate its control plane.', 'Changes the current-release link and records history. Does not roll back user data, vendor packages, or external service changes.', 'update rollback'),
'export': ('Export an inventory of the workstation configuration and registered resources.', 'Writes ~/DeckExports. This private inventory can include host addresses and personal paths; use support-bundle for sanitized diagnostics.', 'export'),
'emulation bios-audit': ('Inspect expected BIOS locations and optionally an import source without copying firmware.', 'Read-only. Supply your own legally obtained files; the project ships no BIOS payloads.', 'emulation bios-audit --source ~/BIOS'),
'emulation bios-import': ('Copy BIOS files from a user-provided directory into the established emulator BIOS location.', 'Copies local firmware files. Does not download BIOS or ROMs; ensure the configured emulation destination is mounted.', 'emulation bios-import --source ~/BIOS'),
'media setup': ('Create browser-backed media applications, launchers, and Desktop shortcuts.', 'Installs/configures the browser integration and intentional Desktop icons. Services still require your login; SteamGridDB owns Gaming Mode artwork.', 'media setup'),
'media status': ('Inspect media application files and shortcut integration.', 'Read-only. Presence does not verify subscriptions, login sessions, or DRM playback.', 'media status'),
'media keeper setup': ('Install or open the Keeper password-manager integration.', 'May install the application and open account setup. Passwords and vault contents are never collected by support-bundle.', 'media keeper setup'),
'media keeper status': ('Check whether Keeper integration is available.', 'Read-only. Does not inspect vault contents or verify credentials.', 'media keeper status'),
'network test': ('Report network diagnostics and optionally test a registered streaming host.', 'Performs network probes and reads local connectivity information. Inspect individual results; diagnostic output may include network addresses.', 'network test --host desktop --json'),
'health': ('Summarize module, storage, backup, and operational readiness.', 'Read-only summary. Inspect individual readiness states; use verify for an aggregate automation exit status.', 'health --json'),
 'terminal status': ('Inspect installed terminal tools, prompt selection, shell integration, and tmux configuration.', 'Read-only. Returns nonzero if the managed terminal stack is incomplete.', 'terminal status --json'),
 'terminal apply': ('Install the user-space terminal stack and apply managed shell, prompt, font, and tmux configuration.', 'May download tools and fonts and update managed configuration. --config-only avoids tool downloads; --refresh rechecks/downloads upstream assets.', 'terminal apply --config-only'),
 'terminal reset': ('Remove managed terminal integration and eligible managed tool files.', 'Uses installation receipts to preserve modified or unmanaged files. --keep-tools retains installed binaries/fonts. Review status before resetting.', 'terminal reset --keep-tools'),
 'terminal font-check': ('Check the configured Nerd Font using local font discovery.', 'Read-only. A missing font can cause prompt glyphs to render incorrectly.', 'terminal font-check'),
 'terminal prompt status': ('Show the selected prompt engine and managed prompt configuration.', 'Read-only. Supports Oh My Posh and Starship.', 'terminal prompt status'),
 'terminal prompt use': ('Choose Oh My Posh (posh) or Starship for managed shells.', 'Updates prompt selection and shell integration. Open a new shell to see the result.', 'terminal prompt use starship'),
 'terminal tmux status': ('Inspect the managed tmux configuration and available executable.', 'Read-only. Does not create or stop tmux sessions.', 'terminal tmux status'),
 'terminal tmux apply': ('Apply the project’s managed tmux configuration.', 'Writes user configuration; existing sessions may require reloading the config.', 'terminal tmux apply'),
 'controller status': ('List captured controller layouts and detect Valve source templates.', 'Read-only. Does not create directories or alter Steam Input state.', 'controller status'),
 'controller recommend': ('Recommend a Steam Input layout strategy for a game, application, or emulator.', 'Read-only guidance. Community rankings are not automatically selected.', 'controller recommend "World of Warcraft"'),
 'controller discover': ('Find personal Steam Input VDF exports in Steam Controller Configs.', 'Read-only. Export a layout in Steam first if none are listed.', 'controller discover'),
 'controller capture': ('Copy a selected VDF layout into the project’s named controller-layout collection.', 'Writes a copy and metadata under ~/.config/deckctl/controller-layouts. Does not change the currently active per-game layout.', 'controller capture "My Layout" --source ~/layout.vdf'),
 'controller install-templates': ('Install captured layouts and available Valve desktop layout into Steam’s templates directory.', 'Copies templates without editing live per-game state. Steam normally discovers them when entering Gaming Mode; restart Steam only if its picker remains cached.', 'controller install-templates'),
 'controller open': ('Open the Steam controller-configuration page for a numeric App ID.', 'Launches a steam:// URL through xdg-open. Requires Steam and a graphical session.', 'controller open 12345'),
 'library audit': ('Inspect Steam shortcut targets, exact duplicates, artwork slots and managed Desktop icons.', 'Read-only. Uses every discovered Steam account independently. Missing or unresolved targets are reported without executing them. Use library repair to review safe repairs; SteamGridDB remains the Gaming artwork owner.', 'library audit --json'),
 'aliases': ('List convenience shell aliases and the deckctl command each invokes.', 'Read-only. Aliases are installed by control-plane setup; open a new shell to load them.', 'aliases'),
 'desktop apply': ('Install project-owned Desktop icons and repair known project shortcut icon references.', 'Writes user icon files and known project .desktop entries only. SteamGridDB retains Gaming Mode artwork ownership.', 'desktop apply'),
 'desktop status': ('Inspect project Desktop icon files and known shortcut icon references.', 'Read-only. Reports missing or stale integration independently of Steam artwork.', 'desktop status'),
 'decky plugins': ('Audit selected Decky plugins and Decky Loader readiness.', 'Read-only. Checks real plugin structure; an orphaned plugin directory does not prove Loader is active.', 'decky plugins'),
 'decky select': ('Interactively choose the project’s desired Decky plugins.', 'Writes selection state. Installation is performed by install-selected or the normal installer.', 'decky select'),
 'decky selected': ('Print the current desired Decky plugin selection.', 'Read-only. Selection is distinct from successful installation.', 'decky selected'),
 'decky install-selected': ('Install selected plugins through Decky’s supported plugin-store workflow. Includes the release additions once for older saved selections; preserves later opt-outs and existing plugin settings.', 'Requires functioning Decky Loader and network access. --dry-run plans only; --reinstall replaces existing selected plugins; --yes accepts applicable prompts. Failure is reported instead of inventing successful receipts.', 'decky install-selected --dry-run'),
 'decky receipts': ('Display recorded Decky plugin installation receipts.', 'Read-only. Receipts are historical evidence; use plugins to inspect current state.', 'decky receipts'),
 'decky theme install': ('Apply the project’s CSS component stack using CSS Loader.', 'Compatibility entry point for decky css apply. Bubble Gum Rave is a palette applied to supported settings, never a standalone fake theme.', 'decky theme install'),
 'decky theme status': ('Inspect the project CSS component/palette status.', 'Read-only compatibility entry point. Use decky css status for the primary interface.', 'decky theme status'),
 'decky css status': ('Inspect installed Theme Store components, palette configuration, and CSS Loader integration.', 'Read-only. Checks persisted state and receipts; missing prerequisites remain visible.', 'decky css status'),
 'decky css apply': ('Obtain required real components through CSS Loader’s Theme Store and apply the Bubble Gum Rave palette.', 'Uses the installed plugin’s native backend and advertised configurable controls. Validates persisted settings. Requires CSS Loader; unsupported controls are reported and no fake theme or raw Git clone is installed.', 'decky css apply'),
 'decky css guide': ('Explain the CSS Loader component and palette workflow.', 'Read-only guidance describing prerequisites, components, and profile recovery.', 'decky css guide'),
 'decky css profiles': ('List live CSS Loader profiles and project-captured profile copies.', 'Read-only. CSS profiles are separate from deckctl hardware profiles.', 'decky css profiles'),
 'decky css capture': ('Capture one named or all live CSS Loader profiles for recovery.', 'Copies exact profile settings and assets into ~/.config/deckctl/css-profiles. Returns configuration-required when no live profile exists.', 'decky css capture'),
 'decky css restore': ('Restore one named or all captured CSS Loader profiles.', 'Writes the live CSS profile directory and retains displaced profiles for rollback. Reload CSS Loader/Steam when instructed.', 'decky css restore'),
 'android status': ('Inspect real Waydroid image, installation, and readiness state.', 'Read-only. An existing shortcut alone does not prove Android is installed.', 'android status --json'),
 'android install': ('Launch the established SteamOS Waydroid installer.', 'Uses the protected vendor workflow. Choose Android 13 with Google Play when prompted. If user state is missing after installation, opens the bundled launcher; close Android after first-run setup to resume provisioning. May request sudo; Google login remains interactive.', 'android install'),
 'android retry': ('Complete Android setup using the existing image when available.', 'Skips READY installations. For an existing image without user state, opens Android_Waydroid_Cage.sh in Desktop Mode. Close Android to resume provisioning. If the launcher is missing, runs protected host repair. Fresh installs use the vendor wizard. Never downloads a replacement image merely because user state is missing.', 'android retry'),
 'android repair': ('Run the established protected Waydroid host-integration repair.', 'Preserves the upstream protected repair and Android data. May request sudo and stop/restart services. Opens the bundled launcher afterward only if first-run user state is missing.', 'android repair'),
 'android reinstall': ('Deliberately recreate Android through the upstream protected archive workflow.', 'Disruptive operation: launches the baseline reinstall flow and its state-protection prompts. Prefer retry or repair for ordinary recovery.', 'android reinstall'),
 'workspace status': ('Inspect optional Notion, ChatGPT, and Claude desktop-style web applications.', 'Read-only. Does not verify account login or service availability.', 'workspace status --json'),
 'workspace setup': ('Create the optional workspace web applications and Desktop shortcuts.', 'Writes browser app launchers and intentional Desktop icons. Each service requires its own account authentication.', 'workspace setup'),
 'workspace notion-mcp': ('Print guidance for connecting a supported agent to Notion MCP.', 'Read-only. Does not create credentials or authorize account access.', 'workspace notion-mcp'),
 'setup run': ('Resume incomplete guided setup or retry a named step.', 'Rechecks actual component state before skipping. --step ID selects one step; interrupted/failed/deferred states persist. A missing component cannot be marked complete. Required account/GUI interaction remains visible. READY is detected; CONFIRMED is user-confirmed configuration. Exit 2 means incomplete setup.', 'setup run --step android'),
 'setup status': ('Show guided setup progress and how to resume.', 'Read-only. Does not create a shortcut or mark steps complete.', 'setup status'),
 'setup open': ('Open the persistent setup launcher in the desktop environment.', 'May refresh the setup shortcut and launch a terminal. Requires a graphical Desktop Mode session.', 'setup open'),
 'setup cleanup': ('Remove verified, unchanged installer shortcuts staged by this project.', 'Runs automatically after module provisioning and guided steps. Rechecks actual component readiness and file hashes; keeps incomplete installs, modified/untracked files, symlinks, application launchers, recovery copies and unrelated Downloads/ZIP files. Exact legacy EmuDeck downloader copies are recognized. --dry-run reports without deleting. This is not a general disk cleaner.', 'setup cleanup --dry-run'),
 'setup reset': ('Clear recorded guided-setup completion for a named step or all steps.', 'Changes progress bookkeeping only; does not uninstall applications or delete account data.', 'setup reset'),
 'help': ('Display the full manual entry for any registered command or command group.', 'Read-only. Equivalent to adding --help at the selected command level. Unknown command paths return usage error 2.', 'help decky css apply'),
 'setup report': ('Report component readiness, interrupted operations and exact retry commands.', 'Read-only; --json gives structured output. READY requires a detector; CONFIRMED identifies user-confirmed account setup. Failed, stale or deferred steps remain visible. Exit 2 means setup needs attention, 1 means recorded module failure. Module readiness is rechecked; JSON also includes the last apply attempt.', 'setup report --json'),
 'update preview': ('Compare a candidate release with the currently installed control plane.', 'Read-only except temporary archive extraction. Requires --archive FILE or --source DIRECTORY. Lists added/changed/removed release files, pending Decky additions and preserved user state. Does not execute candidate code, download plugins or promote releases.', 'update preview --archive ~/Downloads/steamdeck-workstation-v0.2.26.tar.gz'),
 'storage verify-migration': ('Compare preserved Emulation content with the mounted DECK-EMU destination.', 'Read-only SHA-256 comparison of all source files and directory entries, including saves, BIOS and ROMs. Extra destination files are retained. Missing cards, symlinks needing review and mismatched files return 2; --json emits results. Close emulators before verification/finalization.', 'storage verify-migration --json'),
 'library repair': ('Preview or apply backed-up repairs for known Desktop icons and exact duplicate Steam shortcuts.', 'Without --yes, preview only. --duplicates opts into removing byte-equivalent parsed records within each Steam account; --user limits those Steam repairs to one account. Steam must be closed for VDF edits. Original files are retained under state/shortcut-rollback. Missing executables are reported, never guessed. Gaming artwork remains owned by SteamGridDB.', 'library repair --duplicates --yes'),

}

ARGUMENTS = {
'json':'Emit machine-readable JSON instead of the human-readable report.',
'module':'Registered module ID, such as decky or terminal; omit where allowed to cover enabled modules.',
'minimal':'Also stop the Decky plugin service while entering safe mode.',
'game':'Game title to evaluate; quote spaces.',
'system':'Emulation system identifier used to tailor the recommendation.',
'yes':'Accept this command’s confirmation prompts; prerequisite checks still run.',
'name':'Name of the registered object, bundled profile, or capture; see DESCRIPTION and EXAMPLES.',
'launcher':'Launcher identifier to record for this game.',
'path':'Existing game installation path; quote spaces.',
'storage_role':'Storage role associated with the registered game.',
 'target':'Host address for registration, or game/application title for controller advice.',
 'mac':'Wake-on-LAN MAC address in six-byte colon-separated form.',
 'relay':'SSH destination (user@hostname) on the remote host’s local network.',
 'sunshine_port':'Sunshine TCP probe port (default: 47984; range: 1..65535).',
 'timeout':'Maximum number of seconds to wait for host reachability (default: 90).',
 'out':'Output file for profile export; output directory for remote host-kit.',
 'archive':'Path to a trusted archive. Restore can prompt when omitted; update can download from the configured release source.',
 'description':'Task description; quote as one argument when it contains spaces.',
 'source':'Existing local source file or directory; see DESCRIPTION for the required format.',
 'host':'Name of a previously registered Sunshine host.',
 'config_only':'Apply managed configuration without downloading terminal tools.',
 'refresh':'Refresh upstream terminal tool assets instead of relying on the existing installation.',
 'keep_tools':'Retain managed tool binaries/fonts while removing terminal integration.',
 'engine':'Prompt engine: posh (Oh My Posh) or starship.',
 'appid':'Numeric Steam application ID whose controller page should open.',
 'reinstall':'Reinstall selected Decky plugins even when currently installed.',
 'dry_run':'Show intended Decky plugin operations without installing them.',
 'step':'Guided setup step ID; omit to reset all recorded progress.',
 'command':'Command path to document, for example: decky css apply.',
}

FILES = '''FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.
'''

def walk(parser, path=()):
    yield path, parser
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                yield from walk(child, path + (name,))

def decorate(root):
    for path, parser in walk(root):
        key=' '.join(path)
        children=next((a.choices for a in parser._actions if isinstance(a,argparse._SubParsersAction)), {})
        if key in PAGES:
            description, effects, example=PAGES[key]
        elif children or not path:
            description = ('Operate the Steam Deck workstation.' if not path else 'Manage ' + key + ' operations using the commands below.')
            effects = 'Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.'
            if key == 'update': effects += ' With no subcommand, update runs update check.'
            example = (key + ' ' + next(iter(children))) if children else 'help'
        else:
            raise ValueError(f'Command has no manual entry: {key}')
        parser.allow_abbrev=False
        parser.formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, width=88)
        parser.description=f'NAME\n  deckctl {key} — {description}\n\nDESCRIPTION\n  {effects}'
        parser.epilog=(f'EXAMPLES\n  deckctl {example}\n\n' + FILES +
            '\nEXIT STATUS\n  0  Operation/report completed. Read per-item states in diagnostic reports.\n  1  Operation failed, or a required component is absent.\n  2  Invalid command usage or a documented configuration-required state.\n  Vendor subprocess errors may propagate their own nonzero status.\n\nSEE ALSO\n  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl\n')
        for action in parser._actions:
            if isinstance(action,argparse._SubParsersAction):
                action.title='COMMANDS'
                # argparse's pseudo-actions drive the group summary listing.
                action._choices_actions=[]
                for name in action.choices:
                    full=' '.join(path+(name,))
                    summary=PAGES[full][0] if full in PAGES else f'Manage {full} operations.'
                    action._choices_actions.append(action._ChoicesPseudoAction(name, [], summary))
            elif action.dest not in ('help','version'):
                action.help=ARGUMENTS.get(action.dest, action.help)
                if not action.help: raise ValueError(f'Undocumented argument: {key} {action.dest}')

# Optional container commands keep their domain documentation with the implementation.
from .containers import HELP as CONTAINER_HELP
PAGES.update(CONTAINER_HELP)
