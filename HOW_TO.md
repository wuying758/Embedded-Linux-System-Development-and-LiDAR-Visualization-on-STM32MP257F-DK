# Build, Deployment, and Verification

## 1. Required environment

1.1 Hardware

 - STM32MP257F-DK, A35-TD flavor, running ARM64 Linux on Cortex-A35.
 - microSD card of at least 16 GB, suitable board power supply, USB data cables.
 - ST-LINK virtual serial console at 115200 baud; board console: /dev/ttySTM0.
 - USB DRD data connection for DFU flashing and optional USB networking.
 - 1024 x 600 HDMI display.
 - SLAMTEC RPLIDAR C1 connected through a CP2102N USB adapter to a USB Host port;
   baud rate 460800, supported by the cp210x and usbserial kernel modules.

1.2 Software baseline

 - Host: native Ubuntu / Kubuntu 22.04, x86_64, Bash.
 - STM32CubeProgrammer 2.23.0, Linux x86_64 edition.
 - Matching STM32MP2 A35-TD FLASH, SDK, and SOURCES packages: v26.02.18.
 - OpenSTLinux Weston distribution 5.0.15, Yocto scarthgap.
 - SDK: aarch64-ostl-linux- toolchain, GCC 13.4.0.
 - Linux 6.6.116 plus the official ST v6.6-stm32mp-r3 patch.
 - external-dt-v6.0-stm32mp-r3, using stm32mp2/a35-td/linux.
 - gcnano-driver-stm32mp-6.4.21-r1, rebuilt to produce a matching galcore.ko.
 - Bundled SLAMTEC RPLIDAR SDK 2.1.0.
 - Board GUI: Python 3, PyGObject, GTK 3, PangoCairo, pycairo, Weston/Wayland,
   stdbuf, and fontconfig.

Run the commands below on the host environment specified above. Connect the
board's USB data port to the host running STM32CubeProgrammer.

1.3 Project files

 - scripts/env-v26.02.18.sh: portable SDK/build environment entry point.
 - docs/SOURCE_PACKAGE.md: source package contents and setup instructions.
 - vendor/ostl-linux/: Linux, external device tree, and GPU source
   archives in the source package. The environment helper selects this directory
   when present.
 - kernel-hello-world/add-boot-greeting.patch: kernel greetings and startup delay.
 - kernel-hello-world/README.md: explanation of the kernel greeting and delay.
 - apps/hello-world/: basic Hello World source and Makefile.
 - apps/serial-menu/hello_world_example.c: final user-space menu source.
 - apps/serial-menu/serial-menu.profile and apps/serial-menu/serial-getty-menu.conf: login hook and
   systemd mount dependency.
 - apps/serial-menu/Makefile: application build/install rules.
 - docs/stm32mp257-reproduction/assets/weston.ini: HDMI output configuration.
 - lidar/rplidar_sdk-master/: bundled official SDK source snapshot.
 - lidar/ui/: GUI sources, launcher, desktop entry, icons, font, and tests.
 - lidar/scan-verification.log and verification-summary.json;
   lidar/ui/rplidar-ui-verification.json and .png: test logs, reports, and screenshot.

Keep these relative paths when copying the project. STEP 0 covers package
preparation and SDK installation. Download SOURCES only when vendor/ostl-linux/
is absent; the source package includes the required BSP components there.

Use scripts/env-v26.02.18.sh for the build commands in this README.

## 2. Project changes and implementation scope

2.1 Kernel source: init/main.c

Baseline: Linux 6.6.116 AFTER applying ST's 0001-v6.6-stm32mp-r3.patch.
kernel-hello-world/add-boot-greeting.patch contains two changes:

 (1) In start_kernel(), immediately after console_init(), print:
     Hello World from the start of Linux kernel!
 (2) In kernel_init_freeable(), immediately after do_basic_setup(), print the
     kernel greeting, sleep for approximately 10 seconds, then print Continue!:

```c
do_basic_setup();

pr_notice("Hello World from Linux kernel!\n");
msleep(10000);
pr_notice("Continue!");
```

msleep(10000) suspends the init thread for approximately 10 seconds.
linux/delay.h is already included. pr_notice() writes the greeting to the kernel log.
The greeting and delay run before user-space login.

Apply the ST patch first and this project patch second, once each, as in STEP 1.
The project kernel patch modifies init/main.c.
The matching source snapshot is kernel-hello-world/reference/init/main.c.

2.2 User-space source and Makefile

Build apps/serial-menu/hello_world_example.c in STEP 2. It adds read_line(), show_greeting(),
and a menu loop supporting the greeting, uname() kernel release, text echo,
countdown, and return to the shell. It disables stdout buffering and discards
the unread remainder of oversized input lines. STEP 2 copies it to the build
directory as hello_world_example.c.

The supplied Makefile uses SDK CC/CPPFLAGS/CFLAGS/LDFLAGS, builds the executable,
and stages installation under install_artifact/usr/local/bin. STEP 2 shows the
complete build and upload commands.

2.3 Startup and display configuration

 - serial-menu.profile adds a terminal check to root's .profile and runs the menu
   only on /dev/ttySTM0. The root home is discovered from /etc/passwd in STEP 2.
 - serial-getty-menu.conf adds [Unit] RequiresMountsFor=/usr/local to the serial
   getty. The menu runs through the serial login hook; disable the earlier
   hello-world.service if installed. SSH keeps its regular shell.
 - weston.ini changes HDMI-A-1 from mode=1920x1080 to the 1024 x 600 timing in
   STEP 1.8, and changes DSI-1, DPI-1, and LVDS-1 from mode=preferred to mode=off.
 - STEP 1 adds a versioned kernel/device-tree boot entry and keeps existing boot
   entries. Its APPEND arguments are read from the target's boot configuration.

2.4 Added GUI and unchanged vendor components

 - lidar/ui/scan_model.py: parses SDK scan text, assembles frames, and manages the
   acquisition subprocess, device ownership, errors, stop, and restart.
 - lidar/ui/lidar_ui.py: GTK 3 drawing and controls for start/stop, display pause,
   radius, Q filtering, nearest distance, point inspection, and board verification.
 - lidar/ui/rplidar-ui: selects the board's Wayland session and starts Python.
 - rplidar-ui.desktop, radar.svg/.png, and fonts/: desktop entry, icons, and Chinese
   font support; retain the bundled font license.
 - scripts/env-v26.02.18.sh: new portable host environment helper. It locates this
   project from its own path, honors explicit directory overrides, and validates
   the selected SDK.

LiDAR acquisition uses the bundled official SDK/example. Linux provides the
cp210x and usbserial drivers. The external device tree and GPU driver use the
official sources: select the A35-TD tree and rebuild galcore.ko for the new kernel.
Boot firmware uses the matched Starter Package binaries.

## How to use
If you received the source archive, place it and its .sha256 file in the same
directory, then extract and check it [HOST]:

```bash
sha256sum -c stm32mp257-source-v26.02.18.tar.gz.sha256
tar -xzf stm32mp257-source-v26.02.18.tar.gz
cd stm32mp257-source-v26.02.18
sha256sum -c SHA256SUMS
```

Use this extracted directory for all steps below. It includes the required BSP
sources. Obtain the matched SDK, FLASH image, and programmer in STEP 0.

STEP 0: Choose paths, install prerequisites/SDK, and boot a fresh board.
STEP 1: Prepare source, apply patches, build, deploy, and verify the kernel.
STEP 2A: Build/deploy the basic user-space Hello World.
STEP 2: Build/deploy the final user-space menu and install its login hook.
STEP 3: Build/deploy the official C1 acquisition program.
STEP 4: Check board dependencies and deploy the GUI.
STEP 5: Run the demonstration and verification checks.

Commands marked HOST run in host Bash. Commands marked BOARD run after serial
or SSH login to the target. Use one host terminal for builds/uploads and another
for the picocom serial connection. Keep build variables in the first terminal;
a host variable is not automatically available in a board terminal. Stop at any
failed command. Build as your normal user; use sudo for host administration.

## STEP 0 - Set up the host and board

0.1 Install host dependencies [HOST, before loading the SDK]

```bash
sudo apt-get update
sudo apt-get install build-essential bc bison flex patch xz-utils \
    libssl-dev libelf-dev libncurses5-dev libncursesw5-dev libyaml-dev \
    u-boot-tools git picocom libusb-1.0-0 openssh-client python3 unzip file kmod
```

0.2 Choose working directories [HOST]

Open Bash in the copied project root, the directory containing this README.
The following are defaults you may change. Use writable build paths without
whitespace; the SDK and vendor makefiles do not reliably support such paths.
Set connection parameters after discovering the devices in Section 0.5.

```bash
export PROJECT_ROOT="$(pwd -P)"
test -f "$PROJECT_ROOT/apps/serial-menu/hello_world_example.c"
export STM32_DEV_ROOT="$PROJECT_ROOT/work/Developer-Package"
export DOWNLOAD_DIR="$PROJECT_ROOT/downloads"
export SDK_DIR="$STM32_DEV_ROOT/SDK-v26.02.18"
export STM32_PROGRAMMER_DIR="$PROJECT_ROOT/tools/STM32CubeProgrammer"
export JOBS=4
mkdir -p "$STM32_DEV_ROOT" "$DOWNLOAD_DIR" "$PROJECT_ROOT/tools"
```

PROJECT_ROOT is the project root directory. Set STM32_DEV_ROOT to the build
location and SDK_DIR to the SDK installation directory. In a new
terminal, open the project root, restore any overrides, and source
scripts/env-v26.02.18.sh AFTER the SDK installation in Section 0.4.
The helper defines KERNEL_SRC_DIR, EXTDT_LINUX_DIR, GPU_SRC_DIR, OUTPUT_BUILD_DIR,
and artifact. Section 0.5 sets the board and serial connection variables.

Paths such as /boot, /lib/modules, /etc, and /usr/local below refer to the board.

0.3 Obtain matched downloads and install STM32CubeProgrammer

Select version v26.02.18 of the STM32MP2 A35-TD packages from ST:
 - Starter: https://www.st.com/en/embedded-software/stm32mp2starter.html#get-software
 - SDK/Sources: https://www.st.com/en/embedded-software/stm32mp2dev.html#get-software
 - Programmer: https://www.st.com/en/development-tools/stm32cubeprog.html

Save FLASH and SDK in DOWNLOAD_DIR. Download SOURCES there if vendor/ostl-linux/
is absent. Select the x86_64 Linux A35-TD SDK. If ST adds an en. prefix, set the
variables to the real filenames.

```bash
export FLASH_ARCHIVE="$DOWNLOAD_DIR/FLASH-stm32mp2-openstlinux-6.6-yocto-scarthgap-mpu-v26.02.18.tar.gz"
export SDK_ARCHIVE="$DOWNLOAD_DIR/SDK-x86_64-stm32mp2-openstlinux-6.6-yocto-scarthgap-mpu-v26.02.18.tar.gz"
export SOURCES_ARCHIVE="$DOWNLOAD_DIR/SOURCES-stm32mp-openstlinux-6.6-yocto-scarthgap-mpu-v26.02.18.tar.gz"
file "$FLASH_ARCHIVE" "$SDK_ARCHIVE"
if [ ! -d "$PROJECT_ROOT/vendor/ostl-linux" ]; then
    file "$SOURCES_ARCHIVE"
fi
```

Download/unpack the Linux STM32CubeProgrammer installer, run its .linux installer,
and choose STM32_PROGRAMMER_DIR as the installation directory. Use version 2.23.0.
Then install its supplied USB access rules [HOST]:

```bash
export programmer="$STM32_PROGRAMMER_DIR/bin/STM32_Programmer_CLI"
test -x "$programmer"
sudo cp "$STM32_PROGRAMMER_DIR"/Drivers/rules/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
"$programmer" --help
```

0.4 Install the SDK and unpack the outer source/Starter archives [HOST]

Use new destination directories. Do not extract over a modified source tree or
overwrite an installed SDK. Follow the SDK installer's prompts as a normal user.

```bash
tar -xf "$SDK_ARCHIVE" -C "$STM32_DEV_ROOT"
export SDK_INSTALLER="$STM32_DEV_ROOT/stm32mp2-openstlinux-6.6-yocto-scarthgap-mpu-v26.02.18/sdk/st-image-weston-openstlinux-weston-stm32mp2.rootfs-x86_64-toolchain-5.0.15-openstlinux-6.6-yocto-scarthgap-mpu-v26.02.18.sh"
bash "$SDK_INSTALLER" -d "$SDK_DIR"
if [ ! -d "$PROJECT_ROOT/vendor/ostl-linux" ]; then
    tar -xf "$SOURCES_ARCHIVE" -C "$STM32_DEV_ROOT"
fi
mkdir -p "$STM32_DEV_ROOT/Starter"
tar -xf "$FLASH_ARCHIVE" -C "$STM32_DEV_ROOT/Starter"
source "$PROJECT_ROOT/scripts/env-v26.02.18.sh"
printf 'ARCH=%s\nCROSS_COMPILE=%s\n' "$ARCH" "$CROSS_COMPILE"
${CROSS_COMPILE}gcc --version
```

The helper loads SDK_DIR/environment-setup-cortexa35-ostl-linux, installed by the
SDK installer. Expected ARCH=arm64 and CROSS_COMPILE=aarch64-ostl-linux-. It checks
OECORE_SDK_VERSION for v26.02.18 and reports a missing/wrong SDK. Use a fresh Bash
terminal if a different SDK was previously loaded. For future build sessions,
source the portable helper again, restoring custom path settings first.

0.5 Flash a fresh board and establish serial/SSH access

If the board already runs the matching Starter system, skip flashing. Otherwise
flashing replaces the selected microSD contents. With power disconnected, set
BOOT0..3 to OFF for DFU, insert the SD card, connect USB DRD to the host and
ST-LINK/power as required, then power on. List DFU devices and set DFU_PORT from
the output. The index can change after reconnecting [HOST]:

```bash
"$programmer" -l usb
```

Set DFU_PORT to the listed device, then flash [HOST]:

```bash
export DFU_PORT=USB1  # Replace with the port listed above.
cd "$starter_original/images/stm32mp2"
"$programmer" -c "port=$DFU_PORT" \
    -w flashlayout_st-image-weston/optee/FlashLayout_sdcard_stm32mp257f-dk-ca35tdcid-ostl-optee.tsv
```

Run the write command from images/stm32mp2 so TSV-relative image paths resolve.
After successful flashing, power off, set BOOT0=ON and BOOT1..3=OFF for A35-TD
SD boot, connect HDMI and display power, and power on. Verify the ST-LINK device
with ls /dev/serial/by-id/ or ls /dev/ttyACM*. HOST_SERIAL may differ. In another
host terminal, set HOST_SERIAL and open the console:

```bash
ls -l /dev/serial/by-id/
export HOST_SERIAL=/dev/ttyACM0  # Replace with the ST-LINK serial device.
sudo picocom -b 115200 "$HOST_SERIAL"
```

Wait for initial partition resizing to finish. Log in as root if prompted.
Inspect board interfaces in the serial terminal [BOARD]:

```sh
uname -a
ip -br addr
```

Keep the serial connection open to observe reboots and use the board shell.
To close picocom when finished, press Ctrl+A, then Ctrl+X.

Set BOARD_HOST to the board's USB or Ethernet IP address shown by ip -br addr,
without the subnet suffix. For example, if the board shows 192.168.7.1/24, set
BOARD_HOST to 192.168.7.1 and configure an unused host address on the same subnet,
such as 192.168.7.2/24. Identify the host USB interface with ip -br link and use
the host network settings to configure it. The direct link requires no default
gateway. Check that the board SSH service is active, then verify [HOST]:

```bash
export BOARD_HOST=192.168.7.1  # Replace with the address shown on the board.
export BOARD="root@$BOARD_HOST"
ssh "$BOARD" 'uname -m; cat /etc/os-release; df -h /boot /lib/modules'
```

## STEP 1 - Build and deploy the kernel changes

1.1 Unpack component sources and apply patches [HOST, SDK loaded]

Extract the three component archives, then apply the ST patch and project patch
in that order. Run this preparation once for a fresh source tree. For later
builds, keep the prepared sources and continue from Section 1.3.

```bash
tar -xf "$BSP_SRC/external-dt-v6.0-stm32mp-r3-r0/external-dt-v6.0-stm32mp-r3-r0.tar.xz" \
    -C "$BSP_SRC/external-dt-v6.0-stm32mp-r3-r0"
tar -xf "$BSP_SRC/linux-stm32mp-6.6.116-stm32mp-r3-r0/linux-6.6.116.tar.xz" \
    -C "$BSP_SRC/linux-stm32mp-6.6.116-stm32mp-r3-r0"
tar -xf "$BSP_SRC/gcnano-driver-stm32mp-6.4.21-r1-r0/gcnano-driver-stm32mp-6.4.21-r1-r0.tar.xz" \
    -C "$BSP_SRC/gcnano-driver-stm32mp-6.4.21-r1-r0"
cd "$KERNEL_SRC_DIR"
patch --batch --forward --dry-run -p1 < ../0001-v6.6-stm32mp-r3.patch &&
patch --batch --forward -p1 < ../0001-v6.6-stm32mp-r3.patch
patch --batch --forward --dry-run -p1 < "$PROJECT_ROOT/kernel-hello-world/add-boot-greeting.patch" &&
patch --batch --forward -p1 < "$PROJECT_ROOT/kernel-hello-world/add-boot-greeting.patch"
```

Both dry runs must succeed. If either fails, inspect the source and patch state
before continuing. Confirm the two changes described in Section 2.1.

1.2 Configure an out-of-tree build [HOST]

Use the supplied kernel configuration for the STM32MP257F-DK. It sets the release
label to -custom, disables automatic Git suffixes, and includes serial-console,
logging, CP2102N, and module support.

```bash
cd "$KERNEL_SRC_DIR"
mkdir -p "$OUTPUT_BUILD_DIR"
cp "$PROJECT_ROOT/kernel-hello-world/kernel-build.config" "$OUTPUT_BUILD_DIR/.config"
make O="$OUTPUT_BUILD_DIR" olddefconfig
```

The environment helper sets neutral kernel build user and host strings. Read
the generated release from include/config/kernel.release after compilation.
For a later deployment that must retain this release as a fallback, change
CONFIG_LOCALVERSION to a new label and rebuild the image and matching modules.

1.3 Build and stage the kernel, device tree, and modules [HOST]

```bash
cd "$KERNEL_SRC_DIR"
make -j"$JOBS" O="$OUTPUT_BUILD_DIR" Image.gz vmlinux dtbs \
    KBUILD_EXTDTS="$EXTDT_LINUX_DIR" &&
make -j"$JOBS" O="$OUTPUT_BUILD_DIR" modules &&
make O="$OUTPUT_BUILD_DIR" INSTALL_MOD_PATH="$artifact" INSTALL_MOD_STRIP=1 modules_install
```

After all build/install commands succeed, stage the exact board device tree:

```bash
export kernel_release="$(cat "$OUTPUT_BUILD_DIR/include/config/kernel.release")"
mkdir -p "$artifact/boot"
cp "$OUTPUT_BUILD_DIR/arch/arm64/boot/Image.gz" "$artifact/boot/"
cp "$OUTPUT_BUILD_DIR/arch/arm64/boot/dts/st/stm32mp257f-dk-ca35tdcid-ostl.dtb" \
    "$artifact/boot/"
printf 'Deploy this release: %s\n' "$kernel_release"
```

1.4 Rebuild the GPU module against this kernel [HOST]

```bash
cd "$GPU_SRC_DIR"
make -j"$JOBS" SOC_PLATFORM=st-mp2 DEBUG=0 \
    O="$KERNEL_BUILDDIR" M="$PWD" AQROOT="$PWD" -C "$KERNEL_BUILDDIR"
${CROSS_COMPILE}strip --strip-debug galcore.ko
test "$(modinfo -F vermagic galcore.ko | awk '{print $1}')" = "$kernel_release"
mkdir -p "$artifact/lib/modules/$kernel_release/extra"
cp galcore.ko "$artifact/lib/modules/$kernel_release/extra/"
depmod -b "$artifact" "$kernel_release"
```

The galcore.ko vermagic release must equal kernel_release. OUTPUT_BUILD_DIR is the build
directory; artifact is a host staging directory, not the host's root filesystem.

1.5 Upload versioned files [HOST]

Check free space, the mounted /boot, and the existing extlinux configuration.
The new release must differ from the running release to retain its modules as
a fallback. If the new release is already installed, choose a new LOCALVERSION
and rebuild all matching modules before this procedure.

```bash
ssh "$BOARD" 'uname -r; df -h /boot /lib/modules; cat /boot/mmc0_extlinux/extlinux.conf'
test "$(ssh "$BOARD" uname -r)" != "$kernel_release"
rm -f "$artifact/lib/modules/$kernel_release/build" \
    "$artifact/lib/modules/$kernel_release/source"
scp -O "$artifact/boot/Image.gz" "$BOARD:/boot/Image.gz-$kernel_release"
scp -O "$artifact/boot/stm32mp257f-dk-ca35tdcid-ostl.dtb" \
    "$BOARD:/boot/stm32mp257f-dk-$kernel_release.dtb"
scp -O -r "$artifact/lib/modules/$kernel_release" "$BOARD:/lib/modules/"
```

Only remove the staging directory's build/source links, which refer back to host
paths. The stock kernel/device tree and existing module releases remain in place.
scp -O selects the legacy SCP protocol for transfer to the board.

1.6 Add the boot entry [HOST, after all uploads succeed]

This block targets the matched Starter Package's /boot/mmc0_extlinux layout.
It checks required files, backs up the configuration once, reads the existing
root/console arguments, and writes a new default entry. Inspect the existing
APPEND lines first; the first entry supplies the root arguments below.

```bash
ssh "$BOARD" /bin/sh -s -- "$kernel_release" <<'BOARD'
set -eu
release=$1
conf=/boot/mmc0_extlinux/extlinux.conf
backup="$conf.before-custom"
test -s "/boot/Image.gz-$release"
test -s "/boot/stm32mp257f-dk-$release.dtb"
test -s /boot/st-image-resize-initrd
test -d "/lib/modules/$release"
depmod -a "$release"
if [ ! -e "$backup" ]; then
    cp -a "$conf" "$backup"
fi
root_args=$(awk '$1 == "APPEND" { $1=""; sub(/^[ 	]+/, ""); print; exit }' "$backup")
test -n "$root_args"
{
    printf 'DEFAULT CustomKernel\n'
    sed '/^[[:space:]]*DEFAULT[[:space:]]/d' "$backup"
    cat <<ENTRY

LABEL CustomKernel
        MENU LABEL Custom Kernel Hello World
        KERNEL /Image.gz-$release
        FDT /stm32mp257f-dk-$release.dtb
        INITRD /st-image-resize-initrd
        APPEND $root_args loglevel=7
ENTRY
} > "$conf.new"
mv "$conf.new" "$conf"
cat "$conf"
sync
BOARD
```

Quoting the outer BOARD delimiter preserves literal U-Boot ${console}/${baudrate}
variables. The block recreates the project entry from the saved backup, avoiding
duplicates; if other boot settings were
changed since that backup, merge those changes deliberately before rerunning it.

1.7 Reboot and verify

Keep the serial terminal open before rebooting [HOST]:

```bash
ssh "$BOARD" 'sync; reboot'
```

The SSH connection closes during reboot. Observe the early greeting, followed
later by the kernel greeting and Continue! approximately 10 seconds apart.
Other kernel threads can print during that interval. After login [BOARD]:

```sh
uname -r
dmesg | grep -E 'Hello World|Continue!'
modinfo -F vermagic galcore
lsmod | grep galcore
```

Require uname -r to match the build release, the greeting/delay to be observable,
and galcore vermagic to match with the module loaded. Configure HDMI in Section 1.8.
If needed,
check /proc/cmdline for the serial console and loglevel=7. If the new kernel
cannot boot, select a retained entry in the serial bootloader menu. When a board
shell is accessible, restore the previous default [BOARD]:

```sh
cp -a /boot/mmc0_extlinux/extlinux.conf.before-custom /boot/mmc0_extlinux/extlinux.conf
sync
reboot
```

1.8 Configure HDMI output

In /etc/xdg/weston/weston.ini, update the [output] sections for the 1024 x 600
HDMI display:

 - HDMI-A-1: replace mode=1920x1080 with the custom timing shown below.
 - DSI-1, DPI-1, LVDS-1: change mode=preferred to mode=off.

The resulting output sections are:

```ini
[output]
name=HDMI-A-1
mode=49.5 1024 1072 1168 1312 600 603 613 624 -hsync -vsync

[output]
name=DSI-1
mode=off
transform=rotate-90
app-ids=1000

[output]
name=DPI-1
mode=off

[output]
name=LVDS-1
mode=off
```

The supplied docs/stm32mp257-reproduction/assets/weston.ini contains these
changes. Upload it, back up the board configuration, install it, and restart
Weston [HOST]:

```bash
scp -O "$PROJECT_ROOT/docs/stm32mp257-reproduction/assets/weston.ini" "$BOARD:/tmp/custom-weston.ini"
ssh "$BOARD" /bin/sh -s <<'BOARD'
set -eu
test -f /etc/xdg/weston/weston.ini
if [ ! -e /etc/xdg/weston/weston.ini.before-custom ]; then
    cp -a /etc/xdg/weston/weston.ini /etc/xdg/weston/weston.ini.before-custom
fi
install -m 0644 /tmp/custom-weston.ini /etc/xdg/weston/weston.ini
systemctl restart weston@root
BOARD
```

Confirm that the HDMI screen displays the Weston desktop at 1024 x 600.
To restore the original configuration, copy weston.ini.before-custom back to
weston.ini and restart weston@root.

## STEP 2A - Build and deploy the basic user-space Hello World

Run on the host with the SDK loaded:

```bash
export HELLO_BUILD="$STM32_DEV_ROOT/build/hello-world"
mkdir -p "$HELLO_BUILD"
cp "$PROJECT_ROOT/apps/hello-world/hello_world_example.c" "$HELLO_BUILD/"
cp "$PROJECT_ROOT/apps/hello-world/Makefile" "$HELLO_BUILD/"
make -C "$HELLO_BUILD" clean
make -C "$HELLO_BUILD" && make -C "$HELLO_BUILD" install
${CROSS_COMPILE}strip --strip-unneeded "$HELLO_BUILD/install_artifact/usr/local/bin/hello_world_example"
file "$HELLO_BUILD/install_artifact/usr/local/bin/hello_world_example"
scp -O "$HELLO_BUILD/install_artifact/usr/local/bin/hello_world_example" "$BOARD:/tmp/basic-hello-world"
ssh "$BOARD" 'mkdir -p /usr/local/bin && install -m 0755 /tmp/basic-hello-world /usr/local/bin/hello-world'
```

Run on the board:

```sh
/usr/local/bin/hello-world
```

The program prints a greeting, counts from 10 to 0, prints its closing message,
and exits. Its installed name is hello-world. The extended serial menu uses
hello_world_example, so both applications can be installed together.

## STEP 2 - Build and deploy the serial menu

2.1 Build from the final source [HOST, SDK loaded]

```bash
export MENU_APP_BUILD="$STM32_DEV_ROOT/build/serial-menu"
mkdir -p "$MENU_APP_BUILD"
cp "$PROJECT_ROOT/apps/serial-menu/hello_world_example.c" "$MENU_APP_BUILD/hello_world_example.c"
cp "$PROJECT_ROOT/apps/serial-menu/Makefile" "$MENU_APP_BUILD/Makefile"
make -C "$MENU_APP_BUILD" clean
make -C "$MENU_APP_BUILD" && make -C "$MENU_APP_BUILD" install
${CROSS_COMPILE}strip --strip-unneeded "$MENU_APP_BUILD/install_artifact/usr/local/bin/hello_world_example"
file "$MENU_APP_BUILD/install_artifact/usr/local/bin/hello_world_example"
```

The result must be an AArch64 ELF executable. clean removes old application
objects so another SDK's output cannot be reused. It does not remove source files.

2.2 Upload and run [HOST]

Exit any running menu with option 0 before replacing the program.

```bash
scp -O "$MENU_APP_BUILD/install_artifact/usr/local/bin/hello_world_example" \
    "$BOARD:/tmp/app-hello-world"
ssh "$BOARD" \
    'mkdir -p /usr/local/bin && install -m 0755 /tmp/app-hello-world /usr/local/bin/hello_world_example.new && mv -f /usr/local/bin/hello_world_example.new /usr/local/bin/hello_world_example'
```

Run from the board's interactive shell [BOARD]:

```sh
/usr/local/bin/hello_world_example
```

It prints Hello World, then offers 1) greeting,
2) kernel version, 3) text echo, 4) countdown from 10 to 0, and 0) exit to shell.
Type a number and Enter; option 3 then reads one line to echo. This program runs
in user space after login, independently of the new kernel boot greeting.

2.3 Install the serial-only login hook [HOST]

Copy the supplied configurations. The installation reads root's actual home
directory from /etc/passwd, keeps a backup, and replaces its marked block
idempotently. It does not restart the active serial getty during deployment.

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

The matched image provides root autologin on ttySTM0. Keep picocom connected in
the serial terminal and reboot from the build/upload terminal [HOST]:

```bash
ssh "$BOARD" 'sync; reboot'
```

After reboot, confirm automatic menu launch and working input. Select 0 to
return to the board shell. Reconnect with ssh "$BOARD" in the host terminal and
confirm that SSH opens a regular shell.

To remove menu autostart, delete the BEGIN/END SERIAL MENU block from
root's .profile, remove only the hello-world.conf getty drop-in, and run
systemctl daemon-reload. Keep other profile and getty settings intact.

## STEP 3 - Build and run C1 acquisition

3.1 Rebuild the bundled official SDK [HOST, SDK loaded]

Use the supplied source snapshot instead of downloading an unspecified latest
master. Build a separate working copy, excluding old output/obj/.git directories,
to ensure that binaries from another host are not reused and the supplied source
snapshot remains available for comparison.

```bash
export LIDAR_BUILD="$STM32_DEV_ROOT/build/rplidar-sdk"
mkdir -p "$LIDAR_BUILD"
tar -C "$PROJECT_ROOT/lidar/rplidar_sdk-master" \
    --exclude=./output --exclude=./obj --exclude=./.git -cf - . | \
    tar -C "$LIDAR_BUILD" -xf -
make -C "$LIDAR_BUILD" clean DEBUG= BUILD_TARGET_ARCH=aarch64
make -C "$LIDAR_BUILD" -j"$JOBS" DEBUG= BUILD_TARGET_ARCH=aarch64 \
    CC="$CC" CXX="$CXX" AR="$AR"
${CROSS_COMPILE}strip --strip-unneeded "$LIDAR_BUILD/output/Linux/Release/ultra_simple"
file "$LIDAR_BUILD/output/Linux/Release/ultra_simple"
```

Keep the SDK CC/CXX values including their sysroot arguments. DEBUG= selects the
Release output. Verify an AArch64 executable, then upload [HOST]:

```bash
scp -O "$LIDAR_BUILD/output/Linux/Release/ultra_simple" "$BOARD:/tmp/app-lidar-ultra_simple"
ssh "$BOARD" \
    'mkdir -p /usr/local/bin && install -m 0755 /tmp/app-lidar-ultra_simple /usr/local/bin/rplidar-ultra-simple'
```

3.2 Discover the board serial device and scan [BOARD]

In the serial terminal, select menu option 0 to reach the board shell. Connect
the C1 adapter to USB Host. Check dmesg and /dev/serial/by-id/ or
/dev/ttyUSB*. If necessary load cp210x; usbserial is its dependency. Set the actual
device path below. This board variable is separate from HOST_SERIAL on the host.

```sh
modprobe cp210x
dmesg | tail -n 30
ls -l /dev/ttyUSB*
export LIDAR_DEVICE=/dev/ttyUSB0
/usr/local/bin/rplidar-ultra-simple --channel --serial "$LIDAR_DEVICE" 460800
```

Output should include health status 0 and lines such as
"S theta: 0.21 Dist: 00554.00 Q: 47". theta is degrees, Dist
is millimeters, Q is quality, and S marks scan start. Ctrl+C stops acquisition
and the motor. Stop command-line acquisition before starting the GUI; both use
the same serial device. A missing module requires correcting the kernel build
and deployment, not installing the SDK's user-space library as a kernel driver.

## STEP 4 - Deploy the on-board GUI

4.1 Check board runtime dependencies [BOARD]

The GUI requires python3-core, python3-pygobject, python3-pycairo, libgtk-3.0,
gobject-introspection, coreutils-stdbuf, fontconfig-utils, and weston. These are
included in the specified FLASH package. Check the board runtime:

```sh
python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk, PangoCairo; import cairo; print("GUI imports OK")'
command -v stdbuf
command -v fc-cache
systemctl is-active weston@root
```

All four checks must succeed before continuing. If a dependency is missing,
check that the board uses the FLASH version in Section 1.2.

4.2 Package and upload the sources [HOST]

```bash
export UI_ARCHIVE="$STM32_DEV_ROOT/build/rplidar-ui-install.tar.gz"
mkdir -p "$(dirname "$UI_ARCHIVE")"
tar -czf "$UI_ARCHIVE" -C "$PROJECT_ROOT/lidar/ui" \
    scan_model.py lidar_ui.py rplidar-ui radar.svg radar.png rplidar-ui.desktop fonts
scp -O "$UI_ARCHIVE" "$BOARD:/tmp/rplidar-ui-install.tar.gz"
```

Install on the target [BOARD]:

```sh
mkdir -p /usr/local/share/rplidar-ui /usr/local/share/fonts/rplidar-ui \
    /usr/local/share/applications /usr/local/bin
tar -xmzf /tmp/rplidar-ui-install.tar.gz -C /usr/local/share/rplidar-ui
install -m 0755 /usr/local/share/rplidar-ui/rplidar-ui /usr/local/bin/rplidar-ui
install -m 0644 /usr/local/share/rplidar-ui/fonts/DroidSansFallbackFull.ttf \
    /usr/local/share/fonts/rplidar-ui/
install -m 0644 /usr/local/share/rplidar-ui/rplidar-ui.desktop \
    /usr/local/share/applications/
fc-cache -f /usr/local/share/fonts/rplidar-ui
```

4.3 Launch and operate [BOARD]

Set LIDAR_DEVICE again if this is a new board shell, then launch:

```sh
export LIDAR_DEVICE=/dev/ttyUSB0
/usr/local/bin/rplidar-ui --device "$LIDAR_DEVICE"
```

The window appears on the board's HDMI display. The launcher selects the running
Weston Wayland session. Click Start to begin scanning. The desktop entry uses
/dev/ttyUSB0; use --device when the C1 has another device path.

The GUI uses Chinese labels; their English meanings are:
 - Start / Stop: start/stop acquisition and retain the last frame after stopping.
 - Pause display / Resume display: freeze/resume drawing while acquisition runs.
 - Display radius: choose 1, 2, 4, 6, or 12 m.
 - Minimum quality Q: filter low-quality points; zero distance/quality is excluded.
 - Point information: inspect angle, distance, and quality by hover/selection.
 - Nearest valid distance: nearest Q-valid point in the frame, even outside the
   display radius.

The plot places 0 degrees at the top and increases clockwise. It draws the latest
frame every 100 ms. --auto-start starts acquisition when opening the window.
Closing the window stops its child acquisition process. GUI autostart is not
configured; the serial menu has its own login startup mechanism.

## STEP 5 - Demonstration and verification records

5.1 Reproduction acceptance

 (1) Observe the kernel greetings and approximately 10-second wait over serial.
 (2) Confirm uname -r equals the built release, galcore vermagic matches, its module
     loads, and HDMI works.
 (3) Confirm the menu starts after serial login; try options 1/2/3/4, then 0.
     SSH must still reach the normal shell.
 (4) Show the kernel patch, application source/Makefile, and AArch64 executable.
 (5) Run C1 command-line acquisition, observe health/angle/distance/Q, then stop it.
 (6) Start the GUI, adjust pause/radius/Q, stop and restart acquisition, and close it.
 (7) Optionally run host scan-processing tests [HOST, use system Python]:

```bash
cd "$PROJECT_ROOT"
/usr/bin/python3 -m unittest discover -s lidar/ui -v
```

To rerun the automated hardware GUI check, close the existing GUI and stop
command-line acquisition first. It operates the real scanner [BOARD]:

```sh
/usr/local/bin/rplidar-ui --device "$LIDAR_DEVICE" --verify \
    --report /tmp/rplidar-ui-verification.json \
    --screenshot /tmp/rplidar-ui-verification.png
```

5.2 Test data

 - lidar/scan-verification.log: recorded C1 measurements used by the host tests.
 - lidar/verification-summary.json: acquisition summary.
 - lidar/ui/rplidar-ui-verification.json and .png: board GUI report and screenshot.

Complete Section 5.1 and save the new run's logs. Point/frame counts vary with
the surrounding scene. Verify the rebuilt kernel on the board using Section 1.7.

Official references

 - ST cross-compilation and module deployment:
   https://wiki.st.com/stm32mpu/wiki/How_to_cross-compile_with_the_Developer_Package
 - STM32MP257x-DKx board connections and boot switch settings:
   https://wiki.st.com/stm32mpu/wiki/STM32MP257x-DKx_-_hardware_description
 - Linux 6.6 kernel logging:
   https://docs.kernel.org/6.6/core-api/printk-basics.html
 - Linux 6.6 sleep/delay APIs:
   https://www.kernel.org/doc/html/v6.6/timers/timers-howto.html
 - SLAMTEC SDK upstream (use the bundled snapshot for this reproduction):
   https://github.com/Slamtec/rplidar_sdk
