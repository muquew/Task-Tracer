# 4.15.1 最终交付清单

交付状态：**已完成**。最终收口时间：**2026-10-25 22:56:47.015408 UTC**。本轮v6的本地完整73与正常标准CI已通过；工件公开下载与真实生产业务亦已完成。本页是最终补充scope；原阶段根README、coverage及manifest保持原始身份。

## 当前v6冻结与工件

| 项目 | 已确认值 |
| --- | --- |
| 应用提交 | `6a3b8e61ba0699cc316fd92a247cc9c917a7521d` |
| 23项源码集合 | `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54` |
| 84项验证输入集合 | `1d0a6604a369bd42c75045692eb11536ae9636ee6f4320a0d4e07c4a65ca9561` |
| index.html | `89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30` |
| final-freeze-v6 inputs.json | SHA `f2c62095210b338ab126286ba8b7d62adefb05743269d8f3fc84179872a34a22` |
| clean canonical正式包 | 992,071字节／24文件，`0540eca3d0d83a140c3695f575e24e6c73252afe08e5ae2f4f3457cef4691aca`；两次构建逐字相同，manifest dirty=false，绑定6a3b8e。已选定并完成公开下载逐字核验。 |
| 实际受测包 | 992,071字节／24文件，`6d90cf54ea4c5b7aeb0a601b99da3bd93f70665f62f0231d748d135d19f781c6`；manifest dirty=true，23载荷与clean一致。 |
| 实际4.15.0原包 | 990,442字节／24文件，`02cc67c9ac2a454b9ca248c3a122f92060c674677914dfab567cd7de5f6fbca3`；commit93c990、dirty=false，原包保留未重建。 |

[本轮发行汇总](../release/v6/v6-summary.json)、[原生发行](../release/v6/native/report.json)、[原旧包审计](../release/v6/native/baseline-audit.json)、[clean双构建](../release/v6/canonical/report.json)、[反向证明](../release/v6/canonical/reverse-proof.json)与[24文件清单](../release/v6/canonical/archive-file-list.json)保留原字节。原生发行结束于2026-10-25 22:18:08.823694 UTC，clean双构建结束于22:18:38.351314 UTC；这些是本地验收／构建时间，不能当作发布时间。

实际浏览器发行程序使用保留的dirty受测包。clean包经23载荷逐字一致、仅dirty标记变化及ZIP条目／时间／权限／压缩证明关联；没有宣称clean包另行独立执行完整浏览器运行。原release／upgrade为普通HTTP handler，未附运行时CSP、未设置bypass_csp；正常CSP及生产HTTPS是单独证据范围。

## 当前门槛

[正常v6运行40238448977](https://github.com/muquew/Task-Tracer/actions/runs/40238448977)三引擎均已公开succeeded：Chromium13分25秒（job121304917801）、Firefox11分17秒（job121304917923）、WebKit18分41秒（job121304917994）。checks也已succeeded（33分13秒），整个正常运行公开Success（33分17秒），首次观察整体终态为2026-10-25 22:37:51.161939 UTC。三引擎全部成功曾首次观察于22:23:51.153205 UTC。未见failed-program metadata；上述观察时间均不是服务端精确完成时间。push下deployed_site按条件skipped，不算生产验收。未下载需登录的日志／artifact，不声称直接审计远程73／99原始JSON。

| 门槛 | 实际结果与时间口径 | 原证据 |
| --- | --- | --- |
| v6本地完整73程序 | 通过（73/73）；2026-10-25 22:37:37.764 UTC；实际浏览器system完整Chromium154.0.8037.57（显式/usr/bin/chromium override）。 | [本地原报告](native-v6/full.json) |
| v6正常标准CI整体 | 通过（checks及Chromium／Firefox／WebKit均succeeded）；首次观察到终态：2026-10-25 22:37:51.161939 UTC。 | [正常CI](https://github.com/muquew/Task-Tracer/actions/runs/40238448977)／[公开收据](../final-matrix/remote-ci-v6-standard/receipt.json) |
| v6发行与上一版往返 | 静态7项17.269秒、release4.498秒、真实4.15.0升级／回退／再升级23.100秒，原CLI均exit0。 | [本轮原生报告](../release/v6/native/report.json) |
| v6 10,000×6规模正确性 | 原9组检查通过，108.617秒；原报告结束于2026-10-25 22:20:41.652696 UTC。是合成正确性范围。 | [本轮结果](../release/v6/scale/result.json)／[输入与范围](../release/v6/scale/report.json) |
| 原v5四主题亮暗与短屏审读 | 四主题×亮暗8图及320px错误／放弃2图，10张实看。保留6da原身份，适用文件与v6一致，未重标成v6重跑。 | [原十图](v5-visual-theme-review/README.md) |
| 原v5本地生产driver预演 | 三引擎×桌面／390共6组合，正常CSP／motion；本地HTTP，TLS不适用。保留原身份及同字节依据，不当生产HTTPS通过。 | [原六组合](../production/local-preflight-v5/README.md)／[09、10审读收据](../production/local-preflight-v5/root-visual-review-receipt.json) |
| 原v5 Firefox／WebKit编辑器 | 10/10＋10/10，正常CSP／motion，页面／控制台错误均0；保留6da原身份，与v6应用及helper逐字相同。 | [原专项](v5-editor-safety/README.md)／[原manifest](v5-editor-safety/manifest.json) |
| 工件发布 | 已公开下载，ZIP及校验文件HTTP200，实际字节与0540正式包一致；首次公开下载核验完成于2026-10-25 22:41:44.806214 UTC。 | [发布下载](https://todo.muquew.com/downloads/task-tracer-4.15.1.zip) |
| GitHub→Vercel及域名 | 通过：正常TLS静态资源／安全头匹配，三引擎×桌面／窄屏6/6实际业务及备份通过；2026-10-25 22:54:41.404440 UTC。 | [生产收据](../production/real-domain-v6/receipt.json) |
| 生产真实操作与实际备份 | 6份实际JSON备份的原校验和通过，全部任务字段与导出前／后、刷新后数据库一致，根代理已独立核对。 | [操作／备份收据](../production/real-domain-v6/final-identity/root-final-production-review.json) |

本轮[原生73报告](native-v6/full.json)记录22:04:52.163→22:37:37.764 UTC，73项按登记顺序exit0、completed/passed=true、current_check=null、error=null及0完整性错误；[外层run](native-v6/run.json)统计1965.656秒，stderr0字节。HEAD6a3b8e及107输入首尾相同，实际为系统完整Chromium154.0.8037.57显式override。完整a11y193.948秒／122状态，原release4.319秒。report SHA `9ae4be9880ef9ab4801c901a02e4c7c502b8ccc47358cab543824dcaa4fa56d2`，run SHA `c90533d0e12dcde6fc740acbc61f28ef31785b8ed7f59af093397c272ed94628`；[该scope清单](native-v6/files.json)保留12文件250,462字节。[正常CI归档](../final-matrix/remote-ci-v6-standard/README.md)另行保留公开终态与精确原工作流范围；未取得远程原始报告。

已逐项比较[原v5冻结地图](v5-editor-safety/v5-freeze-inputs.json)与[本轮冻结输入](../release/v6/native/frozen-inputs.json)：23项发行源码及其余83项验证输入逐字相同，唯一改变的原输入是`.github/workflows/checks.yml`的报告步骤。上述视觉、编辑器与本地六组合沿用其实际原metadata和HEAD，只说明同字节适用依据；不将原本地73、WK33、ZIP或CI结果转标为v6完整门槛。

规模程序实际使用system Chromium154.0.8037.57与原reduced-motion、原45秒等预算，任务／子任务全字段及真实导入导出均按原断言核对。不是CI151等价、受控benchmark、真实设备或独立事务故障注入。约17MB实际备份未归档，原下载文件SHA／路径未记录；任务结构指纹不能冒称原下载文件SHA。

## 已发布的静态与下载核验

[发布归档](../production/publication-v6/README.md)保留[原静态收据](../production/publication-v6/attempt-001.json)、[原下载收据](../production/publication-v6/public-package-receipt.json)和原字节清单。

2026-10-25 22:40:44.497897→22:40:49.640611 UTC正常TLS核验通过：原15响应加额外6响应逐字匹配，首页5项安全头按原verify断言匹配；输入地图首尾相同。实际[公开ZIP](https://todo.muquew.com/downloads/task-tracer-4.15.1.zip)与[校验文件](https://todo.muquew.com/downloads/task-tracer-4.15.1.zip.sha256)均HTTP200，ZIP992,071字节／24条目／23载荷与0540及本地tracked文件逐字相同，包内manifest6a3b8e、dirty=false。首次下载核验于22:41:44.806214 UTC完成。main提交7a新增发行下载文件；完整CI仍对应应用6a与相同107输入。元数据提交的`[skip actions]`没有改变workflow、原CLI或产品断言。静态／下载与生产六组合分别保留原始证据。

## 真实域名业务与最终审读

[生产总收据](../production/real-domain-v6/receipt.json)与[原六组合总报告](../production/real-domain-v6/final-identity/native/report.json)记录2026-10-25 22:53:31.074703→22:54:41.404440 UTC，Chromium154／Firefox153／WebKit26.5各1280×900和390×844全部通过。对应耗时为Chromium9.751／9.206秒、Firefox13.855／12.819秒、WebKit13.311／10.636秒。页面／刷新正文均严格匹配index89b，任务全部字段、实际下载JSON校验和和刷新后数据库均按原断言核对，6组pageerrors为空。原exercise及检查函数保持逐字相同，5运行输入、6helpers和7916驱动起末不变。

正常TLS／CSP／动效经既有managed-session代理及公共根CA。Firefox用每视口独立临时NSS信任与官方identity网络协商（包括worker），Chromium／WebKit保持默认协商；四次浏览器启动、六上下文全部关闭，两个临时profile已删。具体传输／清理与[云环境维护说明](../../../../cloud-browser-runtime.md)一致，不是关闭TLS、绕过CSP或应用修复。

[首轮0/6传输阻断](../production/real-domain-v6/attempt-001-transport-failure/README.md)源于未接显式代理／独立Firefox信任；第二轮[4/6原报告](../production/real-domain-v6/attempt-002-default-br-protocol-failure/native/report.json)保留Firefox `br` 的Playwright Response.body协议读取错误。独立[default-br页面／数据／缓存证明](../production/real-domain-v6/transport-probes/firefox-default-br/report.json)正常；只给context header的预检仍失败，最终[浏览器网络identity预检](../production/real-domain-v6/transport-probes/firefox-networking-prefs-identity/report.json)与完整六组合严格通过。没有把default-br Response.body改写为通过，也没有据这次已知传输问题解释旧两次CI WebKit失败。

根代理[最终审读收据](../production/real-domain-v6/final-identity/root-final-production-review.json)于 2026-10-25 22:56:47.015408 UTC 完成：独立比较6份实际备份与导出前／后、刷新后数据库的全部任务字段，核对原checksum通过，并实际打开4张最终代表图。该reviewed_at为本次目标收口时间。生产总报告SHA `a69be7a299614c3eb164be3b576910caf1de206cb8ba4bef66e03441637a564d`，根审读SHA `92b362b97b1c936d70be96b5eebd9372d8ecddd40fa34bf9cd6ecffd34ac84e9`；[生产scope清单](../production/real-domain-v6/manifest.json)独立保留。

## 历史失败与独立证据

- 原6da标准运行[40233014544](https://github.com/muquew/Task-Tracer/actions/runs/40233014544)：checks成功30分9秒、Chromium／Firefox成功，WK22分30秒后exit1，整体Failure30分11秒，公开只见generic exitcode。
- 同6da原配置正常复跑[40235376686](https://github.com/muquew/Task-Tracer/actions/runs/40235376686)：WK再次exit1、26分46秒。两次失败均保留，根因未知，不能称已排除偶发或已修复。v6增加安全状态／源位置可诊断性，未改原四jobs、CLI、33程序、预算或退出语义。
- 原6da本地73：[原报告](native-v5/full.json)SHA `ed64c80c6784fed1f218e596e86fc0803a9cc040d2f70295094b1f0bc1f6514e`，73exit0，完成于21:33:51.036 UTC，2170.187秒，系统完整Chromium154显式override；[run](native-v5/run.json)与[清单](native-v5/files.json)保留6da／58b／62ec，不当当前v6本地73通过。
- 原6da独立本地WK33：[原report](../final-matrix/v5-local-webkit/raw/report.json)SHA `a32df7557093a4bfbe84276d17671f7752077a01f5840b3b7379e6dbb6336c53`，33exit0、1170.275秒、21:40:14.899 UTC完成；[原范围](../final-matrix/v5-local-webkit/README.md)保留live-CDP未跑、非实机／Safari-iOS边界。
- [cfe独立诊断](../final-matrix/remote-ci-webkit-diagnostic-cfe/README.md)job成功，首次观察终态21:44:18.776288 UTC；[公开metadata](../final-matrix/remote-ci-webkit-diagnostic-cfe/public-terminal-status.json)及[106项比较](../final-matrix/remote-ci-webkit-diagnostic-cfe/byte-comparison-proof.json)保留不同workflow身份。未读最终safe table或受保护原JSON，不替代正常标准结果。
- 原6da的4bab clean预备包和8f69受测包保留原身份，[v5发行汇总](../release/v5/v5-summary.json)不作为当前v6工件证明。
- [初始整体验收](../baseline-full/README.md)及[三个安全CI诊断](ci-diagnostics/README.md)保留失败／中断。三个早期诊断均整体失败、只跑checks且未跑兼容性99；其默认通知denied／完整pinned151 granted与原完整smoke通过，支持正式默认launcher选完整Chromium，显式override及原断言保持。临时探针、observer及99排除没有进入正常最终workflow。

## 发布和复现

GitHub main发行工件提交：`7a0a0f13cc9fb2501017f4e2de153a5dec27331d`；正常推送完成观察时间：`2026-10-25 22:40:22 UTC`。应用／完整CI仍绑定6a3b8e；7a相对6a仅新增下载ZIP及校验文件，全部107输入相同。实际生产浏览器与备份结果另列。未查询Vercel后台时不把静态匹配写成后台来源已审计。

复现0540正式工件使用独立干净副本，安装贡献指南依赖后固定检出本轮提交；构建输出置于仓库外，避免新文件改变Git dirty状态：

```bash
git checkout --detach 6a3b8e61ba0699cc316fd92a247cc9c917a7521d
PYTHONDONTWRITEBYTECODE=1 python3 tools/build_release.py --output-dir /tmp/task-tracer-4.15.1-repro
sha256sum /tmp/task-tracer-4.15.1-repro/task-tracer-4.15.1.zip
```

后续发行工件／验收文档HEAD与包内manifest提交可能不同；在其他HEAD重建形成新工件，不能沿用0540校验和。0540正式包与校验文件已通过正常GitHub→Vercel发布，实际HTTPS下载逐字匹配本地正式包；其时间为下载核验完成时刻，不冒称Vercel服务端精确部署完成时间。

任务保存在浏览器资料，任务JSON及视图JSON需独立导出到浏览器外。后台OS通知、真实手机／原生输入法／软键盘／读屏／安装结果见[实机清单](../../../../manual-device-checklist.md)，未执行项保持空白。价格、收款、私密售后和正式商业条款待定；工程收口不等于销售或商业授权上线。

收尾文档与工件不改变已验收的107项输入；原静态7程序再次通过，见[收尾原报告](final-handoff-checks/report.json)。全部六项原始GOAL验收条件保留并标为完成，历史章节保持原文。
