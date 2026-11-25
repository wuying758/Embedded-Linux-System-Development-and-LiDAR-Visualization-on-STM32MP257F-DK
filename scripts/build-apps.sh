#!/usr/bin/env bash
set -e
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/env-v26.02.18.sh"
for app in hello-world serial-menu; do
    build_dir="$STM32_DEV_ROOT/build/apps/$app"
    release_dir="$PROJECT_ROOT/release-assets/$app"
    mkdir -p "$build_dir" "$release_dir"
    cp "$PROJECT_ROOT/apps/$app/hello_world_example.c" "$build_dir/"
    cp "$PROJECT_ROOT/apps/$app/Makefile" "$build_dir/"
    make -C "$build_dir" clean
    make -C "$build_dir"
    "${CROSS_COMPILE}strip" --strip-unneeded "$build_dir/hello_world_example"
    install -m 0755 "$build_dir/hello_world_example" "$release_dir/hello_world_example"
    cp "$PROJECT_ROOT/apps/$app/hello_world_example.c" "$release_dir/"
    cp "$PROJECT_ROOT/apps/$app/Makefile" "$release_dir/"
    cp "$PROJECT_ROOT/apps/$app/README.md" "$release_dir/"
    if [ "$app" = serial-menu ]; then
        cp "$PROJECT_ROOT/apps/$app/serial-menu.profile" "$release_dir/"
        cp "$PROJECT_ROOT/apps/$app/serial-getty-menu.conf" "$release_dir/"
    fi
    file "$release_dir/hello_world_example"
done
