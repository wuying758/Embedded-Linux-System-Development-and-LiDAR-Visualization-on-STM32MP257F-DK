# RPLIDAR C1 Acquisition

The bundled SLAMTEC SDK 2.1.0 contains the library and three Linux examples.
The application uses `ultra_simple` at 460800 baud with the Linux `cp210x` driver.

Build and deployment instructions are in [HOW_TO.md](../HOW_TO.md).
The installed board command is:

```sh
/usr/local/bin/rplidar-ultra-simple --channel --serial /dev/ttyUSB0 460800
```

Select the actual C1 serial device on the board. Stop command-line acquisition
before launching the [GTK interface](ui/README.md).

`scan-verification.log` provides recorded measurement input for the host tests.
`verification-summary.json` contains its aggregate counts and scanner status.
