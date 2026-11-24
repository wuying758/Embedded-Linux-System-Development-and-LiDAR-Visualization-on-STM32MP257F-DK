# User-space Hello World

The application prints a greeting, counts from 10 to 0 with a one-second wait
between numbers, prints its closing message, and exits.

After loading the matching ARM64 SDK environment, run:

```bash
make
make install
```

The executable is `hello_world_example`. Installation is staged under
`install_artifact/usr/local/bin/`. The board installation name is `hello-world`,
so it can coexist with the serial menu. See [HOW_TO.md](../../HOW_TO.md).
