# Firefox 生产域名：正常CA信任预检

**最小可用方案：每个Firefox组合使用全新/tmp NSS profile，导入已配置企业CA公证书，再用官方launch_persistent_context。** 未忽略TLS、关闭证书校验、替换主机解析或导入任意网站leaf；未写系统/root信任、未改App/107/HEAD、未跑任务CRUD或全套33。

[enterprise_roots原失败](enterprise-roots/result.json)保留：Firefox153，显式managed launch/context proxy、`security.enterprise_roots.enabled=True`及`ignore_https_errors=False`，首页仍`SEC_ERROR_UNKNOWN_ISSUER`。

[NSS正常TLS成功](nss-profile/result.json)保留：Firefox153，首页200，source `89b5081b6fe1610c54cd5bab5f87196aad6ff04ecb02a1f30d8bcf0b67d0bc30`，SecurityDetails为TLS1.3、issuer `openai.com`、subject `todo.muquew.com`；同context.request首页也200且source相同，CSP存在，始终`ignore_https_errors=False`。这仅是transport/TLS前检，完整六组合业务由docs代理的新driver另行验收。

使用既有 `NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/environment-proxy-ca.crt`，公证书文件SHA `7fa2d7d439db8bfa7c191457e61af5e3f4eb412314eb148766ac09e93786e4c3`。[公CA元数据](configured-ca-public-metadata.json)确认CA:TRUE；原openssl verify已用现有系统SSL_CERT_FILE确认其本来就可信。`certutil`是既有官方libnss3-tools工具，无需安装依赖。未复制PEM或输出代理凭据。

初始化/import的[安全原命令和退出码](nss-profile-setup.json)及nss-setup-1至4 stdout/stderr完整保留：`certutil -N --empty-password -d sql:<profile>`，随后 `certutil -A -d sql:<profile> -n <nickname> -t C,, -i <configured_public_CA>`。C,,仅为SSL CA信任。API为 `p.firefox.launch_persistent_context(str(profile), headless=True, proxy=managed_proxy, firefox_user_prefs={'security.enterprise_roots.enabled': True}, ignore_https_errors=False, **original_context_options)`；返回Context的`.browser.version`可用。persistent kwargs必须含proxy，context.request也因此走managed path。

[清理收据](cleanup.json)确认context/browser关闭后整个新profile已物理删除。**本目录不含profile/cert9.db/key4.db或其它NSS DB**；只保留安全路径/导入元数据、公CA指纹及正常TLS结果。失败的非persistent browser也已关闭。[主仓库完整性](primary-integrity.json)确认107输入仍逐项匹配已部署main7a0提交。

本次按照cloud-environment-runtime网络说明保留继承的managed proxy与配置CA；environment_status当时policy readiness仍unknown，不把配置状态伪称enforced。实际normalTLS结果是独立的观察证据。原生产0/6报告不改写，新完整六组合由docs单独执行。[本目录清单](manifest.json)排除自身。
