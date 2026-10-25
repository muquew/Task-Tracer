# 旧 v4 冻结候选：完整99原生矩阵

**整体失败：99项调用，98通过、1失败。** Chromium 33/33、Firefox 33/33、WebKit 32/33。旧候选已修复后由新标准CI另验；这里不宣称当前6da/v5 CI已通过，专项诊断也不覆盖此原失败。

本目录阶段名是 `v4-stage`；原外部执行目录实际名为 `final-matrix-v3`，代表当时第三次矩阵尝试。原JSON、日志、命令与路径字段均原字节复制，未把外部v3改写为新v5结果。[原完整说明](raw/README.md)、[原汇总](raw/final-summary.json)、[本归档索引](archive-summary.json)分别保留原结果与阶段说明。

HEAD `2771d561181a4f10afeeacdf2e476dcbb754a49b`；入口 `4a7e54f7c02f1a6d39e7568a4dd55cdc0ce1407847655069b8c27eb1f15304f4`；source23 `574778e1e805a7a70fcc808d158461140cb1bf7c9264ac08f163e3df63c18e92`；verification84 `dfbbc08ec28deb0e028f8318b592f6cc1b9cb5c3270f99ba1cbc19866d013df7`。所有引擎开始/结束均一致。

|原引擎|原报告|结果|用时|
|---|---|---|---:|
|Chromium154.0.8037.57|[native](raw/chromium/native-report.json)|33/33，exit0|1632.286秒|
|Firefox153.0|[native](raw/firefox/native-report.json)|33/33，exit0|1712.703秒|
|WebKit26.5|[native](raw/webkit/native-report.json)|32/33，exit1|2143.829秒|

唯一失败为WebKit `quick_add_recovery_playwright.py` 的分享URL预填流程：原15秒 `#captureShelf` 可见性断言失败；前四节通过，剩余内部用例可能未执行。整份原[失败日志](raw/webkit/native-report-logs/f1bb1cbf-4b9a-4378-9198-e90dcdeb3f2b/webkit-quick_add_recovery_playwright.log)未截断，原keep-going随后完成所有登记程序。

原三命令完整使用 `--group all --keep-going`；HTTP、动画、性能预算、断言及非Chromium CDP子用例例外保持原范围。WebKit真实sysroot与官方仅跳静态宿主预检的flag保留在各原command收据；没有安装成功或实体Safari/iOS认证声明。原[worker关闭](raw/worker-cleanup.json)与[采样后代核对](raw/observed-process-cleanup.json)保留：无活动观测实例，容器待父进程回收的已退出Z记录明确列出，未伪称所有PID消失。

[原文件清单](original-files.json)列出每个实际复制项及107个未复制源码快照的真实原路径、SHA和字节。重复源码树未复制，原完整输入地图、runner、全部关联日志均已复制；没有截断日志或用较宽断言替代失败。原报告绝对路径仍指向原外部运行，复制的relative_path日志已逐项匹配原SHA。

[本范围清单](manifest.json)覆盖实际归档并排除自身。`raw/manifest.json` 是未改的原外部完整清单，仍含外部107快照；该旧清单不表示这些快照已复制。这里不修改初始stage-manifest或其他阶段组件。
