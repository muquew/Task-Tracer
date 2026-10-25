# v6正式包本地复制记录

主代理确认本地原73及同6a标准CI四job成功后给出GO。本目录只归档随后完成的四文件本地复制，**本次操作未stage、commit、push或publish**，后续发布与线上验收另有记录；旧v6候选证据未改写。

复制源是独立clean clone绑定提交 `6a3b8e61ba0699cc316fd92a247cc9c917a7521d` 的4.15.1 ZIP，992,071字节／24文件，SHA `0540eca3d0d83a140c3695f575e24e6c73252afe08e5ae2f4f3457cef4691aca`。manifest dirty=false，23载荷与已验源码逐字相同；没有使用旧6da／4bab包。

[原执行receipt](execution-receipt.json)保留前后全部107输入、HEAD、旧02cc包、四目标SHA／字节、两目标ZIP完整manifest及23载荷核验。[四文件摘要](four-file-copy-summary.json)和[包内integrity原字节](distribution-integrity.json)便于复查。

已复制到 `dist/task-tracer-4.15.1.zip`及`.zip.sha256`、`downloads/task-tracer-4.15.1.zip`及`.zip.sha256`。dist两文件保持Git忽略，downloads两文件供后续跟踪；本操作未暂存。实际旧4.15.0 ZIP02cc保持990,442字节／24文件／93c990 clean未变。源码aggregate58b724、验证aggregate1d0a6604及HEAD6a在前后逐项相同，复制不涉及107输入。

本目录不重复复制ZIP；原ignored dist与拟跟踪downloads就是操作的四个实际目标。source-origins及manifest仅覆盖本目录的执行证据文件，原绝对路径保留捕获身份。
