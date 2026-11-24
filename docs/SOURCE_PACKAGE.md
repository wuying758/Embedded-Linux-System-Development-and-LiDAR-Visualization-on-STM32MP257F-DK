# Source Package

The source release `stm32mp257-source-v26.02.18.tar.gz` contains the repository
sources and the BSP archives needed to reconstruct the kernel, external device
tree, and GPU driver. Install the matched x86_64 SDK and obtain the FLASH image
using [HOW_TO.md](../HOW_TO.md).

## Extract and Verify

```bash
sha256sum -c stm32mp257-source-v26.02.18.tar.gz.sha256
tar -xzf stm32mp257-source-v26.02.18.tar.gz
cd stm32mp257-source-v26.02.18
sha256sum -c SHA256SUMS
```

## BSP Contents

| Directory under `vendor/ostl-linux/` | Contents |
| --- | --- |
| `linux-stm32mp-6.6.116-stm32mp-r3-r0/` | Linux 6.6.116 archive, ST patch, configuration fragments, and upstream instructions |
| `external-dt-v6.0-stm32mp-r3-r0/` | External device tree archive and upstream instructions |
| `gcnano-driver-stm32mp-6.4.21-r1-r0/` | GPU driver archive and upstream instructions |

The environment helper selects `vendor/ostl-linux/` when present. Extract the
component archives, apply the ST kernel patch, and then apply
`kernel-hello-world/add-boot-greeting.patch`. Use
`kernel-hello-world/kernel-build.config` as the build configuration.

The SDK, STM32CubeProgrammer, FLASH image, Git metadata, build caches, and
compiled binaries are distributed separately from this source archive.
Third-party license and copyright files accompany their corresponding content.
