# 首轮生产验收：传输配置阻断（0/6）

这是正式上线后的第一次真实域名验收，原 v5 驱动未修改。实际发布 HEAD 为 `7a0a0f13cc9fb2501017f4e2de153a5dec27331d`，验收源代码提交为 `6a3b8e61ba0699cc316fd92a247cc9c917a7521d`；应用版本 4.15.1、index SHA `89b5081b…`。

Chromium 与 WebKit 的两个全新上下文均已通过主页面正常 TLS、index 与安全头核验，随后资源校验 `APIRequestContext.get(sw.js)` 因 `getaddrinfo EAI_AGAIN` 失败。Firefox 的两个上下文在初始导航因 `SEC_ERROR_UNKNOWN_ISSUER` 失败。六组合均未进入创建任务等业务操作，**不能据此宣称生产业务验收通过**。

[原生总报告](native/report.json)、六个原生组合报告与失败图、[原启动收据](launch/receipt.json)、[本阶段收据](receipt.json)均保留。六个上下文及三个浏览器已关闭，所有绑定输入保持一致。生产模式未启动本地 HTTP 服务。TLS 校验始终启用，没有自动重试。

后续仅能在使用既有 managed-session 代理和已配置公共 CA、保留全部原业务断言的独立预检证明后重新验收。本目录作为原失败证据保持独立。[original-files.json](original-files.json)明确列出已复制和未复制的原文件、大小与 SHA；省略重复 DOM 与冻结源文件，不声称它们已归档。[manifest.json](manifest.json)仅覆盖本目录，排除自身和后续阶段。
