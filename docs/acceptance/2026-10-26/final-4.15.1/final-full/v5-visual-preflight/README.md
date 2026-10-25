# v5 / 89b 公开图与视觉前检

**这是最终候选前的公开图与有限源码证明，不是完整73/99或当前6da标准CI通过记录。** [原完整说明](raw/README.md)及全部原收据字节不变。

|语言|真实任务列表|完整编辑器|
|---|---|---|
|中文|[列表PNG](raw/task-list.png)|[表单PNG](raw/add-task.png)|
|English|[List PNG](raw/task-list-en.png)|[Editor PNG](raw/add-task-en.png)|

入口 `89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30`。原capture只把已验收driver的ROOT改至/tmp候选，正常ProductionHeaderHandler/CSP与动画，Chromium154、1440×1000。每语言经真实编辑器创建6任务、真实控件完成1任务/加入今日计划1任务，再填写完整未保存表单；无数据注入、force或固定sleep。四图逐张实际打开并接受：[capture](raw/capture.json)、[source元数据](raw/source-metadata.json)、[实际helper及输入](raw/locked-inputs-before.json)、[逐图view](raw/visual-review.json)。

拍摄前后source23 `173933e5d6d06c4905e69c0f889d7a3e11bfddf261e6cd7ab415728a6a2140aa`稳定。四张公开图复制后source23为 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`；verification84始终 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`。两组完整身份分别保留在原输入与[复制后输入地图](raw/candidate-inputs-after-png-copy.json)。5runtime、实际helpers及primary2771全107均未变；完整标准CI属于父任务随后固定的新提交，不能把这些前检收据改名为CI通过。

[两函数范围证明](raw/two-function-scope-proof.json)将89b的两个指定函数区间换回primary4a7原区间后，整份index逐字相同；HTML/CSS/日期编辑/DB及其他逻辑字节未改。vercel仅替换唯一变动inline script的CSP hash，其余策略原字节保留。

[原复制收据](raw/clone-copy-receipt.json)确认四项精确复制。英文表单是本次新89b实际捕获，但恰与旧PNG字节相同，所以Git只显示三图变化。原核对器误要求四个SHA都改变而exit1，该执行者错误在[原失败收据](raw/copy-verification-first-attempt.json)保留；正确核对仍逐项要求四目标等于本次外部原图、且无越界写。未把该错误写成产品失败或删掉。

[原文件清单](original-files.json)列出全部实际复制材料；[本范围清单](manifest.json)排除自身。原raw收据中的/tmp及外部绝对路径保留原值，未复制重复源码树或trace到仓库。这里不修改初始stage-manifest或其他组件。
