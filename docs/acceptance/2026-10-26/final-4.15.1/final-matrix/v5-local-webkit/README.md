# v5：独立本地 WebKit 原完整33

**本地结果 passed：33/33通过，0失败，exit 0，1170.275秒。** 这是对6da原标准CI WebKit失败的独立复核；保留原远端失败，不把本地结果改写成远端通过或全项目完成。

[原完整说明](raw/README.md)、[原native报告](raw/report.json)、[派生汇总](raw/summary.json)及[命令/环境](raw/command.json)保留真实全部33原registry、无重试/过滤、原断言/预算/HTTP/动画/CSP范围。完整原日志与stderr在raw，未截断traceback。实际WebKit26.5使用真实sysroot与官方仅跳静态宿主预检flag，实际launch/render与全部产品断言保留；原CDP例外、实体设备未测边界不变。

HEAD6da、source23 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`、verification84 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`起末一致。[输入before](raw/inputs-before.json)、[输入after](raw/inputs-after.json)与native本身均有完整107地图，未重复复制源码树。

[worker清理](raw/worker-cleanup.json)列出原进程组消失、采样后代无活动实例与容器已退出Z记录的准确范围。[原文件清单](original-files.json)逐项给出外部原路径/SHA/bytes及实际复制项，原路径字段保持原值。[本范围清单](manifest.json)排除自身；未修改初始stage-manifest和其它组件。
