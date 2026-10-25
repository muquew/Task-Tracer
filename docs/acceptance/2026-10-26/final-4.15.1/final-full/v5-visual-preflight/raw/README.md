# 89b 真实公开截图与有限源码证明

**四张图已拍摄、逐张实际打开并接受，随后按root释放锁授权精确复制到/tmp候选原四个截图路径。** 未提交或推送，未改primary。

|语言|任务列表|完整编辑器|
|---|---|---|
|中文|[task-list.png](task-list.png)|[add-task.png](add-task.png)|
|English|[task-list-en.png](task-list-en.png)|[add-task-en.png](add-task-en.png)|

沿用已验收capture.py，唯一改动是ROOT指向 `/tmp/task-tracer-final-stable-v5-20261026`。实际Chromium154、1440×1000、正常动画与ProductionHeaderHandler/CSP。每语言通过真实编辑器创建6项任务，通过真实控件完成1项并加入今日计划1项，再填写未保存的完整表单；没有注入任务/数据库、force点击或固定sleep。仅以字体及原动画完成状态等待截图。

[原capture收据](capture.json)、[source元数据](source-metadata.json)、[前置完整输入与11个实际helper来源](locked-inputs-before.json)、[capture结束输入复核](locked-inputs-after-capture.json)及[逐图审阅收据](visual-review.json)绑定实际截图/driver/源码/帮助函数SHA。原capture exit0、stderr0字节、无pageerror；浏览器context和服务均随capture退出关闭。

入口始终 `89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30`。capture前后source23 `173933e5d6d06c4905e69c0f889d7a3e11bfddf261e6cd7ab415728a6a2140aa`、verification84 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`完全稳定；5runtime及实际helper未变。复制公开图后source23为 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`，verification84仍相同。[复制收据](clone-copy-receipt.json)与[复制后107地图](candidate-inputs-after-png-copy.json)逐项绑定。

四张均是本次89b实际浏览器输出。英文表单图恰好与旧图字节相同，所以四项精确复制使Git实际只显示三图内容变化。初次复制后的核对器把“四项已复制”错误写成“四项哈希必须都变”，触发exit1；所有复制与逐文件一致校验在此前已完成。该执行者核对错误在[原失败说明](copy-verification-first-attempt.json)独立保留；修正核对确认四项目标均等于本次外部原图且未改其余输入，未把这次核对失败写成产品失败。

[两函数范围证明](two-function-scope-proof.json)将89b的 `renderProjectFilterOptions` 与 `updateDropdownUI` 两个完整区间替换为primary4a7原区间后，整份index逐字相同；因此HTML、CSS、日期编辑、DB与所有其余逻辑均未改。vercel逐字差异仅对应唯一变动inline script的CSP哈希，没有修改策略其它内容。

本轮仅向clone写四个PNG，primary HEAD2771与全部107输入及原素材逐项不变。完整73/99由root后续按最终107身份执行，本截图工作不代替整体验收。[清单](manifest.json)仅覆盖此外部范围，排除自身。
