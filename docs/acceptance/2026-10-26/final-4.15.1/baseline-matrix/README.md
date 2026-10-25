# 原 4.15.0 三引擎基线

**整体失败：99 个登记程序均已调用，77 通过、22 失败。** 这份记录属于隔离的原基线，不证明最终候选已通过。失败程序可能提前停止其内部子用例。

|实际引擎|调用|通过|失败|用时|原报告|
|---|---:|---:|---:|---:|---|
|Chromium 154.0.8037.57|33|26|7|1107.310 秒|[native-report](raw/chromium/native-report.json)|
|Firefox 153.0|33|25|8|1102.032 秒|[native-report](raw/firefox/native-report.json)|
|WebKit 26.5|33|26|7|1228.276 秒|[native-report](raw/webkit/native-report.json)|

隔离工作树 HEAD `54b95cce891d167617d42bc489cdc801317f00c5`，Git 工作区干净。入口 `bfb0a142fb4c813e17af52267062c6faa63a7a56bd5e41feb335728c1999e9c5`，source23 `131121b361e13fce65d1df18bcc1873478b41098fabf5803620334721e7ff221`，verification84 `a207e5cfd27f752382036e35f15fd62c5dc8fee330b1699ad09aa270262b0a63`；每引擎开始/结束均相同。

[原完整说明](raw/README.md)及[原派生总表](raw/baseline-summary.json)保留八类失败与各条完整日志入口，包括项目范围、重复任务删除/合并、示例、帮助、日历排序、午夜统计，以及 Firefox 导入提醒。后续修复不修改这些结果。原命令均为 `python tools/browser_matrix.py --browser <engine> --group all --keep-going --report <path>`；外层完成退出与原生测试通过有区别。

[原运行库证据](raw/probes/webkit-sysroot.json)与四份完整 ldd 日志证明真实 WebKit 程序依赖均解析成功。原宿主检查失败及 UID1000 下安装失败日志仍在 `raw/probes/`；没有声称系统安装成功。仅 WebKit 使用真实解包库路径 `LD_LIBRARY_PATH=/workspace/.cache/browser-libs/root/usr/lib/x86_64-linux-gnu` 和官方 `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1`，跳过忽略该路径的静态宿主预检；实际渲染、表单操作及原 33 程序保持执行。原[渲染报告](raw/probes/webkit-actual-render.json)、实际打开的[截图](raw/probes/webkit-actual-render.png)与[审阅收据](raw/probes/webkit-render-review.json)仅证明运行库就绪。

保留原 HTTP、动画、视口、预算、断言及原生非 Chromium CDP 时区例外，没有全局 CSP 改写。Linux 引擎和模拟视口不代表实体设备、Safari/iOS、读屏、系统输入法或系统通知投递认证。[清理收据](raw/worker-cleanup.json)确认原三组进程均已结束。

[原文件清单](original-files.json)只覆盖本目录；全部复制项字节与原文件相同。[本目录清单](manifest.json)排除自身。`raw/manifest.json` 是未改写的原外部清单，路径仍相对原外部目录；本归档独立清单覆盖它本身及所有实际复制项。
