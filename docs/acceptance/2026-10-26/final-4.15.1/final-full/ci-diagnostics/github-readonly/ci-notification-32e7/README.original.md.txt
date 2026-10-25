# 通知运行能力诊断：32e7294

[运行40231549681](https://github.com/muquew/Task-Tracer/actions/runs/40231549681)，提交`32e72945975682fdbf20f76e20b7d7db30954d2d`，临时诊断分支：整体Failure，2m59s；[checks](https://github.com/muquew/Task-Tracer/actions/runs/40231549681/job/121284162679) failed，2m56s。原默认检查失败保留。

|公开variant|结果|before_helper → after_helper|
|---|---|---|
|notification_default|AssertionError，smoke_playwright.py:2596:exercise_notifications|permission均denied，state均notificationBlocked；pressed/enabled/两个label枚举均false|
|notification_full|pass|permission均granted，state均notificationDisabled；pressed/enabled=false，label_enable=true|
|smoke_full|pass|原完整smoke，无额外页面读数|

两通知variant均报告Notification=true、lang=zh-CN。成功的原helper执行开→关两次点击，full的after_helper为off符合预期；default失败后的after_helper是第一次点击未成功后的blocked状态，不能误写成它完成了整个开关闭环。

[summary.json](summary.json)逐项保存布尔/白名单枚举及原安全注释。实证支持CI选择已有的完整pinned Chromium以提供原测试需要的通知能力，保留产品断言；尚未证明最终workflow整体通过，也没有修改产品或真实用户权限。

仅GET此新run和两job公开页，没有访问原日志/rawreport、任务、环境、token、受限API或artifact。compatibility按临时诊断条件排除，不能移作最终73/99/main或生产验收。生产driver仍等待main/Vercel匹配信号；primary及任何运行输入未改。`manifest.json`只覆盖本目录并排除自身，与先前两个诊断各自独立。
