# V5 本地生产流程预演归档

这份归档保留已完成的本地预演，不代表网站已发布或真实 HTTPS 验收通过。实际地址是 `http://127.0.0.1:53189/`；使用正常生产 CSP 和正常动效，`bypass_csp=false`、`ignore_https_errors=false`，本地 HTTP 的 TLS 不适用。真实 `https://todo.muquew.com/` 验收尚未执行；这里也不作 Vercel/main、完整73/99套件、真实设备或离线生命周期通过声明。

候选为 HEAD `6da3c7293f08c5d16ca73c7a63d8ff74e17358db`、index `89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30`。source23 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`、verification84 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936` 由[原冻结回执](v5-freeze-inputs.json)记录。归档前后107输入及HEAD均未变；本次没有重新启动浏览器、修改代码或提交。

[原总体报告](local-run/report.json)保留全部6组原结果；[原准备回执](preparation-receipt.json)、[原准备说明](preparation-README.md)、[driver](driver.py)、[复制范围](copy-scope.json)和[原stdout](local-attempt-1.stdout.log)/[stderr](local-attempt-1.stderr.log)按原字节复制。driver仅将旧预期index改为89b，其余代码不变。WebKit使用已建立的sysroot和官方host-precheck标志，只处理主机库预检，不跳过产品断言。

| 原报告 | 浏览器 / 尺寸 | 结果 |
| --- | --- | --- |
| [Chromium桌面](local-run/chromium-1280/report.json) | Chromium154.0.8037.57 /1280×900 | passed |
| [Chromium窄屏](local-run/chromium-390/report.json) | Chromium154.0.8037.57 /390×844 | passed |
| [Firefox桌面](local-run/firefox-1280/report.json) | Firefox153 /1280×900 | passed |
| [Firefox窄屏](local-run/firefox-390/report.json) | Firefox153 /390×844 | passed |
| [WebKit桌面](local-run/webkit-1280/report.json) | WebKit26.5 /1280×900 | passed |
| [WebKit窄屏](local-run/webkit-390/report.json) | WebKit26.5 /390×844 | passed |

每组都是独立新context，通过真实界面创建2条任务、编辑并随主任务保存待输入子任务、完成任务、进入四个视图、切换主题/语言/设置并返回；真实JSON下载由原helper校验checksum及全部任务字段，刷新后再次比较全部任务字段。六组原报告均为page_errors空、context_closed和inputs_unchanged为true；总体报告记录三个browser及本地server均已关闭。每组目录保留原下载JSON、`before-backup-db.json`、`after-backup-db.json`、`final-db.json`。备份操作会更新备份元数据，因此不把整个config在导出前后不变当成结论。

[原运行前指纹](local-run/before.json)和[从原总体报告提取的首尾索引](runtime-helper-maps.json)记录5个runtime、6个实际helper及driver哈希完全一致；后者明确标注为派生索引，不冒充原始报告。原始report的passed字段没有改写。

只保留准备回执中已经实际审读、且本次再次打开核对的3张代表图及原生几何JSON：

- [Chromium桌面统计](local-run/chromium-1280/04-view-stats.png)：2任务中1条已完成，最近7天和项目统计可见；图中也有短暂完成/撤销提示。
- [WebKit窄屏日历](local-run/webkit-390/04-view-calendar.png)：日期网格、选中日期及明细入口可见，短暂完成/撤销提示覆盖下部部分明细，不能用这帧证明下部所有细节无遮挡。
- [WebKit窄屏编辑器](local-run/webkit-390/02-editor-pending-child.png)：日期时间、待保存子任务与固定操作条可见；它是滚动表单的动作截面，不声称整张表单同时在屏幕内。

另保存父agent的[两张最终320px主题图接受回执](root-visual-review-receipt.json)，精确引用已归档的[空日期错误](../../final-full/v5-visual-theme-review/09-berry-dark-320-empty-date-error.png)与[放弃确认](../../final-full/v5-visual-theme-review/10-berry-dark-320-discard-confirmation.png)及其SHA；不重复复制图片，不修改主题证据目录。

[原文件来源清单](original-sources.json)记录所有原路径、SHA256、字节数与复制位置；其他截图、源代码快照及中间状态只列清单，并明确未归档原因。[完整性记录](archive-integrity.json)与[本scope manifest](archive-manifest.json)仅描述此有限本地归档，不是生产发布凭证。旧stage、父manifest和原始JSON均保持原样。
