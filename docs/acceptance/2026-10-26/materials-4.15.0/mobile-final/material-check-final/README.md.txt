# 最终材质回退与系统下拉箭头

最终源码 `bfb0a142fb4c813e17af52267062c6faa63a7a56bd5e41feb335728c1999e9c5`，原ProductionHeaderHandler部署CSP，本地HTTP、新Chromium154资料。实际CDP Emulation.setEmulatedMedia使matchMedia成立，4张原PNG均已逐张打开审读；14个真实UI动作，0页面或运行错误，源码起末相同，浏览器与服务器已关闭。

|步骤|原画面|健康|
|---|---|---|
|1|[减少透明／动态](01-reduced-transparency-and-motion-statistics.png)|接受：两个matchMedia=true，顶栏与底栏不透明且backdrop:none；可见导航的animation／transition≤0.00001秒，0条逾期仍真实disabled。|
|2|[强制系统色任务面板](02-forced-colors-editor.png)|接受：forced-colors=true，外框、表单边界与焦点可见，浮起阴影和主按钮渐变去除。|
|3|[系统下拉箭头](03-forced-colors-system-select-arrow.png)|接受：两个原生select实际appearance:auto／background-image:none；系统黑色箭头在白色控件面清楚可见。|
|4|[恢复正常主题](04-normal-theme-select-arrow-restored.png)|接受：CDP媒体清空，三个matchMedia=false；莓暮SVG箭头逐字恢复且appearance:none，焦点保留、顶栏backdrop blur恢复。|

[原3aa视觉问题](../material-check/report.json)及原4图继续保持，不因最终修复通过而改写。旧20张正常模式图和report／manifest SHA亦核对未变。1条真实UI创建任务的[前后记录](records.json)精确相同。

[最终派生报告](report.json)、[初次来源与原响应头](source.json)、[原会话](session.json)、[动作前后DOM](actions.json)、[文件SHA](files.json)支持上述结论。此范围不是实际OS辅助功能、线上TLS、完整回归或无障碍认证；没有给浏览器原生箭头冒填像素对比度分数。
