# Docker on your Steam Deck

After workstation setup, open a new Konsole window. To activate the aliases in
an existing window, run:

```bash
source ~/.config/deckctl/shell/containers.sh
```

If you upgraded an existing Docker installation, `deckctl containers aliases`
installs the aliases. `docker` and `d` mean the same thing. `docker compose`,
`docker-compose`, `compose`, and `dc` offer the same Compose operations. Existing
commands or personal aliases take precedence.

## Start and check Docker

```bash
deckctl containers start
deckctl containers test
deckctl containers status
docker ps
```

`API_READY` means Docker responds but a container test is still needed. `READY`
means Docker responds and its last matching launch, HTTP and cleanup test
passed; check `last_test_at` for the time. `TEST_FAILED` or `TEST_REQUIRED` means
retry `deckctl containers test` and follow its error guidance. Status is
read-only and does not start containers. A passing test does not validate your app.

For the managed local engine, startup at login is optional:

```bash
deckctl containers autostart on
# To disable automatic startup later:
deckctl containers autostart off
```

This controls user-login startup, not a system service. To stop the managed
engine and all its running workloads, use `deckctl containers stop`.

## Load an image from a tar file

Run from the directory containing the file, or give its full path:

```bash
docker load -i ccc-local.tar
docker images
```

Loading imports an image; it does not start a container. Use the image name and
tag printed by `load` with the application's documented run command or Compose
file. The tar filename is not necessarily the image name. The short form is
`d load -i ccc-local.tar`.

## Start a Compose project

Enter the directory containing your project's `compose.yaml` or
`docker-compose.yml` and configure its required environment values first:

```bash
cd /path/to/your/project
compose config --quiet
compose up -d
compose ps
compose logs --tail 100 -f
```

Ctrl+C stops following logs without stopping the containers. `dc up -d` is the
short form. Use `compose up --build -d` when the project builds local source.
For another file, use `compose -f path/to/compose.yaml up -d`.

To stop temporarily while keeping containers, run `compose stop`. To start
those stopped containers again, run `compose start`. To remove the project's
containers and network, run `compose down`; named volumes are retained unless
you explicitly add `--volumes`. Follow the project's backup instructions before
removing volumes, which may hold databases and other persistent data.

## Inspect or remove individual objects

| Task | Command |
| --- | --- |
| List running containers | `docker ps` |
| Include stopped containers | `docker ps -a` |
| Read a container's logs | `docker logs --tail 100 CONTAINER` |
| Follow logs | `docker logs -f CONTAINER` |
| Open a shell, if the image provides one | `docker exec -it CONTAINER sh` |
| Stop one container | `docker stop CONTAINER` |
| Remove a stopped container | `docker rm CONTAINER` |
| List images | `docker images` |
| Remove an unused image | `docker rmi IMAGE:TAG` |
| List persistent volumes | `docker volume ls` |

Replace uppercase placeholders with names or IDs from the list commands. Removing
a container discards files in its writable container layer; mounted volumes are
separate. Removing an image does not delete the original `.tar` file or uninstall
Docker. Docker refuses to remove images still needed by containers unless forced;
inspect those containers instead of adding force flags blindly.

## If a command does not work

- `docker: command not found`: open a new terminal or source the alias file above.
- Cannot connect to the daemon: run `deckctl containers start`, then `status`.
- Overlay mount failure: rerun `deckctl containers install` interactively; it
  offers the supported repair when safe. See the [storage repair details](../modules/dev/containers/README.md#repair-a-rootless-overlay-mount-failure).
- These aliases apply to Bash/Zsh, not scripts or `sudo`. In scripts use
  `deckctl containers docker -- ...` or `deckctl containers compose -- ...`.
- Commands use the engine selected by deckctl. When using an SSH engine, images,
  containers, volumes, published ports and bind-mount paths belong to that remote
  machine. The managed wrapper does not accept global endpoint/config overrides.

Docker setup details and limitations are in the [container module guide](../modules/dev/containers/README.md).
