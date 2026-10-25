# 独立WebKit安全诊断：cfe

本目录是**独立NEW正常CI诊断旁证**，不是exact6da标准发布门槛，不覆盖首次标准WebKit失败。诊断提交 `cfe8d6de236fa6e771934379c67efd711df5c029` 基于应用提交 `6da3c7293f08c5d16ca73c7a63d8ff74e17358db`，独立分支 `codex/ci-webkit-outcomes-20261026`。主仓HEAD及107输入没有改变。

[公开run](https://github.com/muquew/Task-Tracer/actions/runs/40235171022)直接显示 `Status: Success`、总耗时22m 1s；workflow只定义[一个WebKit job](https://github.com/muquew/Task-Tracer/actions/runs/40235171022/job/121295077000)，因此监控将其映射为job succeeded。该映射不是直接取得job footer或native报告；本次匿名SSR没有匹配单独的job footer终态。起始观察为2026-10-25 21:22:16 UTC，首次终态观察为21:44:18.776288 UTC。各次公开观察未见failed basename／exit annotation。原[终态metadata](public-terminal-status.json)与[观察事件](public-observation-events.jsonl)保留原字节；[公开状态见证](public-terminal-witness.json)明确区分原metadata与派生判断。

## 原范围与安全输出

- [Workflow原字节](diagnostic-workflow.yml)只有一个WebKit job，保留ubuntu-latest、Python3.12、固定requirements／Playwright及原 `install --with-deps webkit`，预算90分钟。
- [Metadata helper原字节](safe-webkit-outcomes.py)启动原 `tools/browser_matrix.py --browser webkit --keep-going --report dist/browser-matrix-webkit.json`，没有过滤33程序、弱化断言或改预算；观察者每5秒只读取本次NEW原生report，输出已知basename、有限数值exit／duration、固定enum和通过数。最终always summary采用同样白名单，不读取／转发原子程序stdout、日志、任务内容、环境或token。
- helper原样返回native退出码。原matrix只有全部33计划完成、无失败退出码／输入完整性错误时返回0。因此公开job成功支持“本次原33全scope native exit0”的判断；**未读取受保护native JSON、原日志或最终table，不声称实际取得或归档这些文件**。

## 与最终源码的关系

[逐文件反证](byte-comparison-proof.json)核对23发行源码及其余83验证输入，106个原文件逐字相同，全部33原程序也逐字相同。诊断仅修改`.github/workflows/checks.yml`并新增metadata helper；后者不在既有84输入合同内。两者均绑定cfe提交原字节。

23源码aggregate仍为 `58b724aff838339caf9c9ba0e2d5cff3ff05d20dae43e5c16fe93984f8734e54`；最终标准84验证aggregate是 `62ec9c75e4045987bfb29df9905d075bbfeb3525558f671c4c26d159aeef0936`，诊断因workflow改变为 `831991ef8562a8b4cb51b4570014eb8ad5e273f1e0c485be4b2b10c63bd611de`，不能把诊断aggregate转标为标准原输入。

首次标准6da run40233014544中的WebKit job121288575649曾Failure，根代理已另行保存原状态。其原日志受保护，后续同源多轮未复现，**根因仍未确定，不能声称已定位或修复**。本次cfe green只保留独立结论；exact6da标准repeat40235376686由主代理另行收口。

本目录没有读取旧受限日志、绕过artifact保护／网络策略，或把其他host作为转发通道。[未复制页面索引](unretained-public-page-index.json)记录原公开HTML捕获路径、SHA和字节，仅保留安全metadata／状态提取，不复制无关站点bootstrap字段。[来源](source-origins.json)与manifest只覆盖本目录实际文件，原绝对路径保持捕获身份。没有提交、发布或复制正式ZIP到主发行目录。
