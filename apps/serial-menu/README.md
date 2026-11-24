# Serial Menu

The menu provides greeting display, running kernel release, text echo,
countdown, and exit to the shell. Option 1 displays the greeting; option 0 exits.

Load the ARM64 SDK environment and run `make` to build `hello_world_example`.
The board executable is installed at `/usr/local/bin/hello_world_example`.

`serial-menu.profile` runs it only during an interactive login on `/dev/ttySTM0`.
`serial-getty-menu.conf` adds the `/usr/local` mount dependency. SSH keeps its
regular shell. Installation and verification commands are in
[HOW_TO.md](../../HOW_TO.md).

To run interaction tests on a host, compile with the host compiler and set
`HELLO_MENU_BINARY` to that executable before running `test_serial_menu.py`.
