# Provisioning and recovery

## Resume setup

Run the normal installer for a fresh or existing Deck. Within the same release,
`deckctl apply` skips a recorded ready module only after its live verifier agrees.
A new release reruns module reconciliation. An interrupted module remains RUNNING
until retried. Vendor scripts retain their existing idempotency checks.

`deckctl setup run` resumes component setup. `deckctl setup run --step android`
retries only Android; use another ID shown by `deckctl setup report`. Missing
components cannot be manually marked complete. Automatically verifiable steps
complete only when the launcher succeeds and their detector agrees.

`deckctl setup report [--json]` reports READY, CONFIRMED, PENDING, INTERRUPTED,
STALE, FAILED, CONFIG_REQUIRED and DEFERRED with exact retry commands. CONFIRMED
means the user confirmed account/pairing setup and the software is present; it
is not credential inspection. Module rows recheck live readiness; JSON also retains the last apply attempt. Exit 2 means unfinished setup; 1 means
recorded module failure. Status and reports do not write progress.

## Review an upgrade

`deckctl update preview --archive FILE` compares a candidate with the current
persistent installation without running candidate code. `--source DIRECTORY`
inspects an extracted release; `--json` emits the full plan. It lists file changes,
Decky additions, preserved user data and remaining authentication/download work.
The normal installer shows this before promoting the control plane. `update apply`
also prints it before validation and promotion. An update changes the control plane;
run `deckctl apply` and `deckctl setup run` to reconcile changed components.

## Shortcut audit and reviewed repairs

`deckctl library audit [--json]` reads each Steam account's shortcuts independently,
checks executable targets, identifies exact duplicate records and examines managed
Desktop icons. A found executable does not prove that its arguments, game payload,
login or launch will work. UNRESOLVED means the target cannot safely be resolved.

`deckctl library repair` previews Desktop icon/permission fixes.
`deckctl library repair --duplicates --user ACCOUNT_ID` adds exact duplicate Steam
record removal for one account. Same-name games with different arguments, tags or
AppIDs are retained. Add `--yes` to apply the reviewed plan. Exit Steam first for
VDF edits. Original files go to state/shortcut-rollback; unchanged record payloads
are copied verbatim and writes are verified. Missing launch targets need the app's
own setup step; deckctl does not guess replacement paths. SteamGridDB remains the
Gaming Mode artwork owner; no images are downloaded or replaced by this repair.

## Restore wizard

Close games/apps that write the selected files. Run `deckctl restore ARCHIVE
--dry-run` to inspect categories, destinations and space requirements. Then run
`deckctl restore ARCHIVE` to select categories interactively. `--category NAME`
can be repeated; `--yes` accepts that selection without a dialog.

The wizard validates all selected paths before writing. It preserves previous
contents under state/restore-rollback, atomically replaces individual files,
retains unrelated destination files, then compares restored SHA-256 hashes. A
result journal identifies verified categories or a failed/interrupted run. A
failure is not a successful restore; its previous files remain in the printed
rollback directory. Restore is atomic per file, not across all categories.

This is a personal-data restore, not a disk image. Applications and logins are
not contained in the save backup: use `deckctl apply`, `deckctl setup run` and
`deckctl verify` afterward. Ambiguous Steam accounts block artwork restoration;
restore other categories until the desired account is unambiguous. Symlinks in
category contents/destinations require review rather than arbitrary traversal.

## Verify an EmuDeck migration

`deckctl storage migrate-emulation` records the original file hashes and opens
the installed EmuDeck manager for its supported migration workflow. It does not
relaunch a staged downloader. Insert the card labeled DECK-EMU first. Close
emulators so saves do not change while comparing data.

`deckctl storage verify-migration [--json]` checks every original directory and
file against the target, including ROMs, BIOS and saves. If the original still
exists, its current contents are authoritative. Otherwise the pre-migration
inventory is used. Extra target files are preserved. Missing cards, changed files,
or unsupported symlinks remain CONFIG_REQUIRED; no source is removed.

`deckctl storage finalize-emulation-migration --yes` rechecks content, renames the
original to an Emulation.pre-deckctl-* rollback folder and links ~/Emulation to
the verified card. Existing correct vendor links are preserved. Check emulator
launches and saves before manually removing a rollback copy. Restore/backup will
refuse a missing recorded card rather than silently writing to internal storage.
