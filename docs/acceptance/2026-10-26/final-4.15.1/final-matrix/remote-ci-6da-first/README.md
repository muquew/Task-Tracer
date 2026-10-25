# 6da3 标准远端CI：首次矩阵失败

固定记录2026-10-25 21:18:37Z的[标准run40233014544](https://github.com/muquew/Task-Tracer/actions/runs/40233014544)，提交`6da3c7293f08c5d16ca73c7a63d8ff74e17358db`，分支`codex/final-stable-delivery-20261026`。**当时整体仍In progress**；此快照不随之后结果改写。

|Job|当时公开结果|时长|
|---|---|---|
|[compatibility (chromium)](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288575939)|succeeded|13m24s|
|[compatibility (firefox)](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288575968)|succeeded|14m52s|
|[compatibility (webkit)](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288575649)|failed|22m30s|
|[checks](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288575952)|已开始，尚无公开完成结论|未结束|
|[deployed_site](https://github.com/muquew/Task-Tracer/actions/runs/40233014544/job/121288576846)|skipped，push条件下属预期|0s|

WebKit公开失败步骤为`Validate critical workflows on desktop and mobile layouts`，原annotation为`Process completed with exit code 1.`。没有90分钟总超时/cancel注释；具体33程序中的哪项失败尚未公开。原日志需要登录，未读取或声称取得raw artifact/report，也没有把旧diagnostic或其他引擎通过移为WebKit通过。

[原结构化快照](snapshot.json)与`evidence/`保存当时run/job公开页面文本；[receipt.json](receipt.json)绑定原路径、SHA-256、提交和来源限制。[manifest.json](manifest.json)只覆盖本子目录且排除自身。checks整体终态将另用新receipt，不覆盖本首次失败证据。

该结果属于候选分支，不能代表main或生产部署。只做正常公开GET与本证据归档，未改HEAD、107运行输入或启动production。
