# STM32MP257F-DK 嵌入式 Linux 开发与激光雷达可视化

项目包括内核启动输出与约 10 秒等待、用户空间 Hello World、串口交互菜单，
以及 RPLIDAR C1 数据采集和板端图形显示。

- `kernel-hello-world/`：内核补丁、构建配置和修改后的源码参考。
- `apps/hello-world/`：问候和倒计时程序。
- `apps/serial-menu/`：问候、内核版本、回显、倒计时及串口登录启动配置。
- `lidar/`：官方 SDK、GTK 界面、字体、图标和测试数据。
- `scripts/`：编译环境和发布构建脚本。
- `docs/`：显示配置和源码包说明。

硬件为 STM32MP257F-DK（A35-TD）、1024 × 600 HDMI 屏幕和 RPLIDAR C1。
使用 v26.02.18 配套 OpenSTLinux 软件包，内核版本为 6.6.116。

完整安装、编译、部署和验证步骤见英文 [HOW_TO.md](HOW_TO.md)。
英文项目介绍见 [README.md](README.md)。

执行 `scripts/build-apps.sh` 可以为两个用户态程序生成去除调试信息的 ARM64
发布文件。镜像和程序附件保存在 `release-assets/`，通过 Releases 发布。
