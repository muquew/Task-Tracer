# 材质回退：原始检查

源码3aa，正常部署CSP本地HTTP，真实CDP媒体偏好。运行断言均通过，浏览器／服务器已关闭，4张原PNG均实际查看。

- [01减少透明](01-reduced-transparency-statistics.png)：matchMedia=true，顶栏和底栏实际变不透明、backdrop:none，零数量禁用保持。
- [02减少动态](02-reduced-motion-editor.png)：matchMedia=true，实际animation/transition最大0.00001秒，焦点可见。
- [03强制系统色面板](03-forced-colors-editor.png)：matchMedia=true，阴影／渐变被移除，必要轮廓和焦点可见。
- [04强制系统色原生select](04-forced-colors-native-selects.png)：**需跟进**。SVG箭头图像保持，但系统控件底变白后箭头仍#D7BCCB，颜色对比约1.76，视觉过淡。建议只在forced-colors内启用系统原生箭头。

运行断言不把这个视觉问题改写成通过；原始actions/session/截图保持，后续若修补另目录保存。旧20张正常模式图与报告没有修改。详见report.json。
