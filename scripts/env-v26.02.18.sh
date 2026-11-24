#!/usr/bin/env bash
# Source from Bash. Install the matching SDK before loading this file.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'Use: source %s\n' "$0" >&2
    exit 1
fi

# Locate this project independently of the current directory or user name.
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)" || return 1
export PROJECT_ROOT
export STM32_WORK_ROOT="$PROJECT_ROOT"
export STM32_DEV_ROOT="${STM32_DEV_ROOT:-$PROJECT_ROOT/work/Developer-Package}"
export SDK_DIR="${SDK_DIR:-$STM32_DEV_ROOT/SDK-v26.02.18}"
if [[ -z "${BSP_SRC:-}" ]]; then
    if [[ -d "$PROJECT_ROOT/vendor/ostl-linux" ]]; then
        BSP_SRC="$PROJECT_ROOT/vendor/ostl-linux"
    else
        BSP_SRC="$STM32_DEV_ROOT/stm32mp-openstlinux-6.6-yocto-scarthgap-mpu-v26.02.18/sources/ostl-linux"
    fi
fi
export BSP_SRC
export KERNEL_SRC_DIR="${KERNEL_SRC_DIR:-$BSP_SRC/linux-stm32mp-6.6.116-stm32mp-r3-r0/linux-6.6.116}"
export EXTDT_DIR="${EXTDT_DIR:-$BSP_SRC/external-dt-v6.0-stm32mp-r3-r0/external-dt-v6.0-stm32mp-r3}"
export EXTDT_LINUX_DIR="${EXTDT_LINUX_DIR:-$EXTDT_DIR/stm32mp2/a35-td/linux}"
export GPU_SRC_DIR="${GPU_SRC_DIR:-$BSP_SRC/gcnano-driver-stm32mp-6.4.21-r1-r0/gcnano-driver-stm32mp-6.4.21-r1}"
export OUTPUT_BUILD_DIR="${OUTPUT_BUILD_DIR:-$STM32_DEV_ROOT/build/linux-custom}"
export KERNEL_BUILDDIR="$OUTPUT_BUILD_DIR"
export artifact="${artifact:-$OUTPUT_BUILD_DIR/install_artifact}"
export starter_original="${starter_original:-$STM32_DEV_ROOT/Starter/stm32mp2-openstlinux-6.6-yocto-scarthgap-mpu-v26.02.18}"
export JOBS="${JOBS:-4}"

if [[ "$PROJECT_ROOT:$STM32_DEV_ROOT:$SDK_DIR:$BSP_SRC:$KERNEL_SRC_DIR:$EXTDT_LINUX_DIR:$GPU_SRC_DIR:$OUTPUT_BUILD_DIR:$artifact" == *[[:space:]]* ]]; then
    printf 'Use paths without whitespace for the SDK and vendor build tools.\n' >&2
    return 1
fi
if [[ ! -r "$SDK_DIR/environment-setup-cortexa35-ostl-linux" ]]; then
    printf 'SDK environment missing: %s/environment-setup-cortexa35-ostl-linux\nInstall the v26.02.18 SDK first; see STEP 0 in the root README.\n' "$SDK_DIR" >&2
    return 1
fi
source "$SDK_DIR/environment-setup-cortexa35-ostl-linux" || return $?
# Use neutral build metadata in generated kernel images.
export KBUILD_BUILD_USER="builder"
export KBUILD_BUILD_HOST="buildhost"
export KBUILD_BUILD_VERSION="1"
export KBUILD_BUILD_TIMESTAMP="2026-11-17 00:00:00 UTC"
if [[ "${ARCH:-}" != arm64 || "${CROSS_COMPILE:-}" != aarch64-ostl-linux- || "${OECORE_SDK_VERSION:-}" != *v26.02.18* ]]; then
    printf 'Expected the STM32MP2 A35-TD v26.02.18 SDK; open a fresh Bash terminal and select the matching SDK_DIR.\n' >&2
    return 1
fi
if [[ -r "$OUTPUT_BUILD_DIR/include/config/kernel.release" ]]; then
    export kernel_release="$(cat "$OUTPUT_BUILD_DIR/include/config/kernel.release")"
else
    unset kernel_release
fi
printf 'Loaded v26.02.18: ARCH=%s, CROSS_COMPILE=%s\nSDK: %s\nKernel source: %s\nBuild output: %s\n' \
    "$ARCH" "$CROSS_COMPILE" "$SDK_DIR" "$KERNEL_SRC_DIR" "$OUTPUT_BUILD_DIR"
