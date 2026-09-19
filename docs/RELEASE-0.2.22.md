# v0.2.22 — provisioning completion

Waydroid first-run provisioning now opens the installed vendor launcher when the
Android image exists but user state does not. This is the launch path confirmed
working on the user's Deck. Close Android after setup/sign-in to resume the
installer. Ready installations are skipped. Explicit host repair still uses the
upstream protected repair; reinstall remains a separate deliberate command.
No generic OTA initialization, image deletion, or Android data migration is added.

The default CSS selection now includes Art Hero, Clean Gameview, Clean Game
Launch, and Focus Highlight Color. Colored Toggles is omitted. All previously
selected components remain, including the requested Percentages, Round, Centered
Game Text, Better Blur, Better Game Badges, Better Achievements, Game Cover
Reflections, and DellyVolume. Themes come through CSS Loader's Theme Store, and
Bubble Gum Rave remains a palette applied through advertised native controls.

Each component is attempted even if another fails. Partial application is reported
as CONFIG_REQUIRED, never READY. Existing configuration is reused on retry.
Existing user-installed Colored Toggles files are preserved; the regenerated
managed profile excludes them. SteamGridDB remains responsible for Gaming Mode
artwork, and CSS recovery/safe mode remain available.

Use the normal installer from the new release. For an already-provisioned Deck,
after updating the control plane, `deckctl decky css apply` reconciles the new set.
The working Android installation is skipped automatically.

Validation uses isolated executable launcher fixtures and the native CSS backend
contract simulator, including persisted settings/profile checks. Live Theme Store
API access is HTTP 403 in this build environment, so real downloads and visual
compatibility of the full selection still need confirmation on Steam Deck.
Google authentication remains interactive.
