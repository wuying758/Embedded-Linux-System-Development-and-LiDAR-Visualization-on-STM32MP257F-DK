# Serial Menu

The menu provides greeting display, running kernel release, text echo,
countdown, and exit to the shell. Option 1 displays the greeting; option 0 exits.

## Prepare the Host and Board

Install the matching STM32MP2 A35-TD v26.02.18 SDK and prepare a board running
the matching OpenSTLinux image. Host dependencies, SDK installation, and board
connection setup are covered in [STEP 0 of HOW_TO.md](../../HOW_TO.md#step-0---set-up-the-host-and-board).

Open Bash in the repository root. Set the working and SDK installation
directories to the locations chosen on your host, then load the SDK:

```bash
export PROJECT_ROOT="$(pwd -P)"
test -f "$PROJECT_ROOT/apps/serial-menu/hello_world_example.c"
export STM32_DEV_ROOT="$PROJECT_ROOT/work/Developer-Package"
export SDK_DIR="$STM32_DEV_ROOT/SDK-v26.02.18"
source "$PROJECT_ROOT/scripts/env-v26.02.18.sh"
```

In the same host terminal, enter the board's actual IP address or hostname.
The following installation commands use a root SSH login to the board:

```bash
read -r -p "Board IP address or hostname: " BOARD_HOST
test -n "$BOARD_HOST"
export BOARD="root@$BOARD_HOST"
ssh "$BOARD" 'uname -m; command -v install'
```

Confirm that the board reports `aarch64` and provides the `install` command.

## Build on the Host

Run in the host terminal with the SDK loaded:

```bash
export MENU_APP_BUILD="$STM32_DEV_ROOT/build/serial-menu"
mkdir -p "$MENU_APP_BUILD"
cp "$PROJECT_ROOT/apps/serial-menu/hello_world_example.c" "$MENU_APP_BUILD/"
cp "$PROJECT_ROOT/apps/serial-menu/Makefile" "$MENU_APP_BUILD/"
make -C "$MENU_APP_BUILD" clean
make -C "$MENU_APP_BUILD" && make -C "$MENU_APP_BUILD" install
${CROSS_COMPILE}strip --strip-unneeded "$MENU_APP_BUILD/install_artifact/usr/local/bin/hello_world_example"
file "$MENU_APP_BUILD/install_artifact/usr/local/bin/hello_world_example"
```

The result must be an AArch64 ELF executable. `make install` copies the
executable into `install_artifact/usr/local/bin/` inside the build directory.
This stages the board directory structure for upload.

## Upload and Run

Exit any running menu with option `0` before replacing the program. Run these
commands on the host:

```bash
scp -O "$MENU_APP_BUILD/install_artifact/usr/local/bin/hello_world_example" \
    "$BOARD:/tmp/app-hello-world"
ssh "$BOARD" \
    'mkdir -p /usr/local/bin && install -m 0755 /tmp/app-hello-world /usr/local/bin/hello_world_example.new && mv -f /usr/local/bin/hello_world_example.new /usr/local/bin/hello_world_example'
```

In an interactive board shell, run:

```sh
/usr/local/bin/hello_world_example
```

Enter a menu number followed by Enter. Option `3` asks for a line of text;
option `0` returns to the shell. Installation is complete for manual use.
The optional steps below enable automatic startup after serial login.

## Start the Menu After Serial Login

`serial-menu.profile` starts the menu during an interactive root login on
`/dev/ttySTM0`. `serial-getty-menu.conf` makes the serial login service wait for
the `/usr/local` mount. SSH sessions open a regular shell.

Run the following on the host. The installation discovers root's home directory,
backs up an existing `.profile`, and replaces the marked menu block when repeated:

```bash
scp -O "$PROJECT_ROOT/apps/serial-menu/serial-menu.profile" \
    "$PROJECT_ROOT/apps/serial-menu/serial-getty-menu.conf" "$BOARD:/tmp/"
ssh "$BOARD" /bin/sh -s <<'BOARD'
set -eu
root_home=$(awk -F: '$1 == "root" {print $6}' /etc/passwd)
test -n "$root_home"
test -d "$root_home"
profile="$root_home/.profile"
if [ -e "$profile" ]; then
    if [ ! -e "$profile.before-serial-menu" ]; then
        cp -a "$profile" "$profile.before-serial-menu"
    fi
else
    touch "$profile"
fi
sed '/^# BEGIN SERIAL MENU$/,/^# END SERIAL MENU$/d' "$profile" > "$profile.new"
{
    printf '\n# BEGIN SERIAL MENU\n'
    cat /tmp/serial-menu.profile
    printf '# END SERIAL MENU\n'
} >> "$profile.new"
/bin/sh -n "$profile.new"
mv "$profile.new" "$profile"
chmod 0644 "$profile"
mkdir -p /etc/systemd/system/serial-getty@ttySTM0.service.d
install -m 0644 /tmp/serial-getty-menu.conf \
    /etc/systemd/system/serial-getty@ttySTM0.service.d/hello-world.conf
if [ -e /etc/systemd/system/hello-world.service ]; then
    systemctl disable --now hello-world.service
fi
systemctl daemon-reload
systemctl cat serial-getty@ttySTM0.service
sync
BOARD
```

The updated hook takes effect on the next root serial login. The matching board
image provides root autologin on `ttySTM0`, so a reboot also starts the menu.
Keep the serial terminal connected, then run on the host:

```bash
ssh "$BOARD" 'sync; reboot'
```

After reboot, confirm that the menu appears and accepts input. Select `0` to
return to the shell. Reconnect over SSH and confirm that it opens a regular shell.

To remove automatic startup, delete the `BEGIN SERIAL MENU` / `END SERIAL MENU`
block from root's `.profile`, remove
`/etc/systemd/system/serial-getty@ttySTM0.service.d/hello-world.conf`, and run
`systemctl daemon-reload` on the board. Keep the other login configuration intact.

## Host Interaction Tests

Open a fresh host terminal without the ARM64 SDK environment. From the repository
root, compile with the host compiler and run the tests:

```bash
cc -Wall -Wextra -o /tmp/hello-menu-host apps/serial-menu/hello_world_example.c
HELLO_MENU_BINARY=/tmp/hello-menu-host python3 apps/serial-menu/test_serial_menu.py
```
