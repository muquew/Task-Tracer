# 远端CI基线：54b95cc

本记录只读审查 [Release checks #23](https://github.com/muquew/Task-Tracer/actions/runs/40222503249)，提交`54b95cce891d167617d42bc489cdc801317f00c5`，总体Failure、46m0s。它属于旧4.15.0基线，不能当作后续4.15.1候选结论。

|Job|公开结果与时长|能够确认的原因|
|---|---|---|
|[checks](https://github.com/muquew/Task-Tracer/actions/runs/40222503249/job/121257061009)|failed，1m8s|验证步骤exit1；具体断言未知|
|[compatibility (chromium)](https://github.com/muquew/Task-Tracer/actions/runs/40222503249/job/121257061006)|failed，12m58s|验证步骤exit1；具体断言未知|
|[compatibility (firefox)](https://github.com/muquew/Task-Tracer/actions/runs/40222503249/job/121257060787)|failed，14m10s|验证步骤exit1；具体断言未知|
|[compatibility (webkit)](https://github.com/muquew/Task-Tracer/actions/runs/40222503249/job/121257060990)|cancelled，45m20s|明确注释：`The job has exceeded the maximum execution time of 45m0s`；随后`The operation was canceled.`|
|[deployed_site](https://github.com/muquew/Task-Tracer/actions/runs/40222503249/job/121257061430)|skipped，0s|push不满足手动verify_site条件，属预期|

33程序矩阵串行并保留失败继续执行，45分钟限制作用于包括安装在内的整个job。root依据此实证仅把WebKit compatibility总预算改为90分钟，其他job仍45分钟；全部原工具断言、工具超时、cases、keep-going和artifact保留。详[配置决定](workflow-adjustment.json)。本审阅者没有修改配置或启动workflow；该决定尚无本记录中的新远端结果。

所有run/job页面通过正常公开HTTPS GET取得。公开页要求`Sign in to view logs`，本记录只保存可见状态/步骤/annotations及HTML哈希，未获取正文日志，不能认定其余exit1就是旧selector，也不声称已修复隐藏失败或远端CI已绿。Node20→24及ubuntu-latest迁移在本次只是warning/notice，未冒充已确认根因。未重试受限API、读取凭据、复制频道签名或执行任何写入/发布。

[run.json](run.json)、[jobs.json](jobs.json)及[原注释文本](run-annotations-visible.txt)给出来源；`evidence/`只含移除script/style后的公开页面文本，不包含脚本内签名。[manifest.json](manifest.json)仅校验本子目录并排除自身，不修改上一级旧阶段manifest。最终本地原检查、最新提交远端CI和正常TLS生产验收仍由各自后续记录给出；生产driver保持待发布状态。
