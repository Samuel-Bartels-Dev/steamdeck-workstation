# Docker hardware check — v0.2.28 candidate

Date: 2026-09-19. Scope: Docker integration on an existing OLED Deck installation,
upgrading the source from v0.2.27 plus the merged storage/alias fixes. This report
is part of the v0.2.28 candidate source; the release tag identifies its final commit.

- SteamOS 3.8.16, build 20260716.1; image default channel stable (active update
  channel not separately verified).
- Kernel 6.16.12-valve24.5-1-neptune-616-gb2f7cfe85e45; internal ext4 storage.
- Rootless Docker 29.8.1, Compose 5.5.1, Buildx 0.37.1; fuse-overlayfs backend.
- Steam client build/channel: not recorded; these Docker checks do not use it.
- Login autostart: off and unchanged.

| Check | Result and evidence |
| --- | --- |
| API-only readiness | PASS: before creating new evidence, `containers status --json` reported API_READY, api_ready true, test_status NOT_RUN, exit 2. |
| Container launch and HTTP | PASS: isolated Compose fixture reached health, returned the expected HTTP body, and its container/network were removed. |
| Readiness after test | PASS: status reported READY, test_status PASSED and a UTC last_test_at timestamp. |
| Dockerfile/Compose/Buildx | PASS: `python3 tests/integration/test_containers_live.py --managed` built a disposable image, checked its build marker and HTTP response, then removed its test resources. |
| Familiar shell commands | PASS in the preceding merged aliases change on this Deck: Bash/Zsh docker/d and Compose aliases; compose up, dc exec and dc down completed a real isolated HTTP test. |
| Guided failure handling | SIMULATED: contract tests cover accepted/declined repair, missing helper, noninteractive setup, existing/new containers, no remote mutation and no retry loop after a fuse failure. The working host's storage was not deliberately broken. |
| Fresh install, LCD hardware, other SteamOS versions, reboot/OS update | NOT TESTED in this report. |
| User application stacks and unrelated workstation modules | NOT TESTED by these Docker checks. |

No SteamOS system files, user project containers, volume data or credentials were
changed by the isolated live test. Repository regression and package validation
are separate release gates and do not extend this report's hardware claims.
