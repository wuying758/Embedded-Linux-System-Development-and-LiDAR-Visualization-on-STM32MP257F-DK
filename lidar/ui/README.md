# RPLIDAR C1 Visualization

A GTK 3 and Cairo interface running on the board's 1024 x 600 HDMI display.
`scan_model.py` parses scan text and manages acquisition; `lidar_ui.py` draws
frames and provides the controls; `rplidar-ui` selects the Weston session.

After installing the files using [HOW_TO.md](../../HOW_TO.md), run on the board:

```sh
/usr/local/bin/rplidar-ui --device /dev/ttyUSB0
```

Click Start to scan. Stop ends acquisition; Pause display keeps acquisition
running while freezing the view. Radius and quality controls filter the plotted
points. Closing the window stops the child acquisition process.

The interface uses Chinese labels. Font assets retain their original license
and copyright files. A screenshot and GUI verification report accompany the
source. Device paths shown in the commands must match the connected C1 adapter.

Host scan-processing tests:

```bash
/usr/bin/python3 -m unittest discover -s lidar/ui -v
```
