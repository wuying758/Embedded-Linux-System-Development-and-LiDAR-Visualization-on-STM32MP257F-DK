# Kernel Greetings and Startup Delay

Target: STM32MP257F-DK, A35-TD, OpenSTLinux v26.02.18, Linux 6.6.116
with the ST `v6.6-stm32mp-r3` patch applied.

The [project patch](add-boot-greeting.patch) modifies `init/main.c`:

1. After `console_init()` in `start_kernel()`, print the early greeting.
2. After `do_basic_setup()` in `kernel_init_freeable()`, print a second greeting,
   wait approximately 10 seconds, and continue.

```c
pr_notice("Hello World from Linux kernel!\n");
msleep(10000);
pr_notice("Continue!");
```

The later delay runs in the init thread. Other kernel activity can continue
while that thread sleeps. Both changes occur before user-space login.

Apply the ST patch first and the project patch second. The source snapshot in
`reference/init/main.c` shows the resulting file. `kernel-build.config` contains
the supplied configuration, with a `-custom` release label.

Follow [HOW_TO.md](../HOW_TO.md) for source preparation, compilation, module and
GPU driver matching, deployment, serial verification, and rollback. The build
environment sets neutral kernel build user and host values.
