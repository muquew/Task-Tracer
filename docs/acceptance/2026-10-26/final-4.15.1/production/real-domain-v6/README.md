# 真实域名生产验收：6/6 通过

实际站点 [todo.muquew.com](https://todo.muquew.com/) 的 4.15.1 已在三引擎、1280×900 和 390×844 六个全新上下文中通过完整原操作检查。验收代码为 `6a3b8e61ba0699cc316fd92a247cc9c917a7521d`；实际发布和本轮首尾 HEAD 为 `7a0a0f13cc9fb2501017f4e2de153a5dec27331d`。index=`89b5081b…`，SOURCE23=`58b724…`，VERIFICATION84=`1d0a6604…`。

|引擎|桌面|窄屏|HTTP 表示范围|
|---|---|---|---|
|Chromium 154|通过，9.751s|通过，9.206s|默认协商|
|Firefox 153|通过，13.855s|通过，12.819s|标准 `identity` 网络协商，包含 worker fetch|
|WebKit 26.5|通过，13.311s|通过，10.636s|默认协商|

[receipt.json](receipt.json)、[根独立复核](final-identity/root-final-production-review.json)和[原生最终总报告](final-identity/native/report.json)链接六个独立报告与真实下载。实际 UI 闭环包括：创建有期限/无期限任务、多行说明与项目标签、编辑并由主保存收纳待输入子任务一次、完成任务、列表/日历/时间线/统计、四套主题/浅深色/中英文、五类设置与返回、真实 JSON 导出和原校验和检查。下载中的每个任务字段与导出前、导出后、刷新后 IndexedDB 完全相同；初始和刷新响应正文均严格匹配 index SHA。六组 pageerrors 均为空。功能用途和证据边界见 [coverage.json](coverage.json)。

所有连接保留正常 TLS、原 CSP 和正常动效，经本云环境已配置的 managed-session 代理及公共根 CA；未忽略证书、禁用 SW、改写响应或缩小业务断言。Firefox 每个视口使用独立临时 NSS profile，仅导入已受系统信任的现有公共 CA。实际共四次浏览器启动、六个上下文，均已关闭；两个临时 Firefox profile 已删除，未归档 NSS/私钥数据库。生产模式没有启动本地 HTTP 服务。应用和 107 项冻结输入未修改；[当前绑定](current-107-input-binding.json)逐项确认字节一致。[驱动适配范围](drivers/final-adapter-scope.json)验证原 `exercise` 和全部原检查函数字节保持不变。

此前失败按原样保留：[首轮 0/6 传输阻断](attempt-001-transport-failure/README.md)；[第二轮原生 4/6 报告](attempt-002-default-br-protocol-failure/native/report.json)。后者 Firefox 在最终 SW 刷新时，Playwright `Response.body()` 对 `br` 响应报 `NS_ERROR_INVALID_CONTENT_ENCODING`。独立 [default-br 证据](transport-probes/firefox-default-br/report.json)证明实际页面、全部任务字段和缓存正文 SHA 正常；该协议读取失败没有改写成通过。仅给 context 添加 identity header 时，worker 仍取 br，故 [该预检](transport-probes/firefox-context-header-identity-incomplete/report.json)仍失败；[浏览器原生网络协商预检](transport-probes/firefox-networking-prefs-identity/report.json)才严格通过原初始/刷新正文、缓存 SHA 和字段检查。因此本次通过明确包含 Firefox 标准 identity 协商，**不宣称 default-br 的 Playwright 正文 API 通过**。外部启动器还曾在任何网络/浏览器执行前因变量顺序退出，[该启动失败](transport-probes/launcher-preexecution-order-failure.json)独立保留。

[screenshots-reviewed.json](screenshots-reviewed.json)列出实际打开审看的六张最终生产图及局限。截图和数量本身不构成易用性证明。这是 Linux 浏览器引擎与视口模拟，未冒充真机、OS 通知、实体 PWA 安装、屏幕阅读器或 IME 验收。生产未执行破坏性导入/清空/恢复；完整本地验收另有原生证明。

[original-files.json](original-files.json)逐项区分本阶段新增的已复制的原 JSON/日志/源码/代表图和未复制的重复 DOM、源快照、其他 PNG，并保留外部路径、大小和 SHA。早期两引擎代理小预检的脚本未独立快照，作为辅助观察而非最终业务通过依据；其驱动哈希和差异保留。正式三引擎预检与最终原生驱动/源码指纹均独立留存。最终六份真实 JSON/DB、根已看四图、原驱动及实际六个 helper 快照归于 `final-identity/`；[运行输入映射](final-identity/runtime-helper-driver-maps.json)和[原始候选冻结快照](final-identity/accepted-freeze-v6.json)保留各自真实时间与状态。[manifest.json](manifest.json)仅覆盖本目录当前明确列出的文件，排除自身和未列出的未来新增；未改任何旧阶段 manifest。
