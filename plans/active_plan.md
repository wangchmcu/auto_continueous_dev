# Active Plan

## 当前目标

- 使用 Codex 长周期算法迭代的本地状态闭环，并保持 tracking 信息优先于原始输入材料。

## 当前实施阶段

- 当前版本：v0.22。
- global plan 文件：`plans/global_plan.md`。
- 当前任务跟踪文件：`plans/version_iterations.md`。
- v0.1 已完成：初始化状态库、记录实验、记录结论、拦截重复路线、生成 handoff、版本任务跟踪、实验命令封装、日志捕获、日志摘要。
- v0.2 已完成：短命令入口、Codex 入口 skill、同会话自动调用流程、端到端演示。
- v0.3 已完成：`raw_input/` 读取边界和 handoff 完整性校验。
- v0.4 已完成：参数空间路线拦截、上下文标题索引和按需读取。
- v0.5 已完成：用自然语言短句触发 session 结束、session 接力和细节查阅流程。
- v0.6 已完成：`auto it self improve` 系统改进沉淀能力。
- v0.7 已完成：intent checkpoint（意图检查点），用于在计划、执行、结果和结束阶段提示 agent 先做安全检查。
- v0.8 已完成：中途记录黑盒入口，用户只说“中途记录一下”时，agent 保存当前接力点但不默认提交推送。
- v0.9 已完成：低假设初始化和 bootstrap checkpoint 规则，避免 AIT 在目标项目中自动发明业务路线；self improve 也能记录并处理二阶改进。
- v0.10 已完成：初始化 bootstrap 把已有 `raw_input/` 作为初期输入源索引和选择性沉淀，但 `init` 不自动吞入原始材料。
- v0.11 已完成：AIT 安装管理增加 `uninstall`，可删除安装命令和 Codex skills，但保留项目状态。
- v0.12 已完成：卸载时给用户选择是否一并删除项目状态目录，并说明各目录存放内容。
- v0.13 已完成：Topic Archive MVP，任何时刻只有一个 active topic，其它 topic 进入 archive 并按需恢复。
- v0.14 已完成：跨平台安装和运行入口，覆盖 Windows Codex app、WSL/Linux Codex CLI、macOS Codex app。
- v0.15 已完成：projection consistency（投影一致性）和 demo/test 历史边界，避免孤儿 Markdown projection 污染恢复上下文。
- v0.16 已完成：topic evidence link（topic 证据关联）MVP，让 topic 能直接关联并查询相关 run、decision 和 artifact。
- v0.17 已完成：多操作系统安装路径体验增强，优先使用已在 `PATH` 且可写的系统推荐命令目录，避免默认落到当前 shell 找不到的位置。
- v0.18 已完成：`auto-iter handoff generate` 默认静默，避免普通 stdout 被 Codex 当 hook JSON 解析；需要人工调试时显式使用 `--print-path`，同时不使用平台特定 shell 重定向以兼容 Windows、WSL/Linux、macOS。
- v0.19 已完成：本地模糊检索增强，使用 BM25（按关键词出现频率和稀有度排序的文本检索算法）、light vector（本地轻量文本向量，不调用额外 LLM（大语言模型）服务）和 graph（由 topic、run、decision、artifact 已有关系组成的结构关系图）帮助找回“之前好像说过某个现象”的候选历史。
- v0.20 已完成：handoff 增加 `Current Baseline`（当前基线：当前被承认为继续开发起点的版本、方法、结果和证据入口）Markdown projection（从已有记录摘出的可读视图，不是新的事实源），只保留主线入口和证据入口。
- v0.21 已完成：项目根目录 `AGENTS.md` 只在已经存在时进入 handoff 读取顺序；`auto-iter init` 不创建它，AIT 也不把它当状态源。
- v0.22 已完成：新增 `auto-iter update` 安装产物更新入口，默认保留项目状态、不运行 `init`，并支持显式 `--check-project`。
- 下一阶段：根据实际使用感受评估 `Current Baseline`、可选 `AGENTS.md` 读取顺序和 `update` 入口是否足以支撑旧项目接管，或继续 topic 生命周期管理增强。

## 下一步

1. 用户说“中途记录一下”“先保存当前状态”“做个阶段记录”等短句时，agent 运行 `auto-iter checkpoint save --text "<用户原话>"`，内部完成 `auto-iter handoff generate` 和 `auto-iter handoff validate` 对应的保存与校验。
2. 中途记录和 session 结束使用相同的状态保存范围；区别是中途记录不默认结束会话、不默认提交、不默认推送。
3. 当用户话语像是在进入计划、执行、结果或结束阶段时，agent 先运行 `auto-iter intent check --text "<用户原话>"`。
4. 用户明确说 `auto it self improve` 时，agent 才运行系统改进沉淀流程。
5. 新项目初始化后保持 `当前业务目标：待用户定义`，直到用户明确确认。
6. 新项目初始化时，agent 运行 `auto-iter context index --include-raw-input` 检查已有 raw input；只按需读取相关章节并用 `raw_input_source` 标注后沉淀。
7. 如果 AIT 在对话中途接入，agent 先整理 bootstrap checkpoint，只记录已确认事实、未决问题和带来源标签的候选项。
8. 用户要求卸载或重新安装 AIT 时，使用 `auto-iter uninstall` 移除安装产物；交互终端让用户选择是否删除项目状态目录，非交互默认保留，除非用户明确要求删除。
9. 用户显式开启、切换、回到或满足 topic 时，agent 使用 `auto-iter topic current/list/show/start/switch/satisfy` 保存和恢复现场。
10. 如果用户 prompt 只是语义上像切换到新 topic，agent 必须先问“是不是已经切入新的 topic 了？”，确认后才切换。
11. 新 session 默认读取 `topics/active_topic.md`，只在用户要求或确认切回 archived topic 时读取 `topics/archive/`。
12. 安装或恢复 AIT 时，按平台选择入口：Windows Codex app 使用 `py -m auto_iteration.cli install` 或 `python -m auto_iteration.cli install`，WSL/Linux Codex CLI 和 macOS Codex app 使用 `python3 -m auto_iteration.cli install` 或 `python -m auto_iteration.cli install`。
13. 恢复上下文或查阅历史时，如果 `context index` 报告 orphan/stale decision projection，agent 不把该 Markdown 文件当作当前结论；先以 SQLite 和 handoff 为准，必要时清理 projection 或把 demo/test 历史迁移到 `examples/` 并写明测试目的。
14. 当某个 topic 有明确相关的 run、decision 或 artifact 时，使用 `auto-iter topic link --topic-id <id> --run-id <run_id> --decision-id <decision_id> --artifact-id <artifact_id> --summary "<摘要>"` 建立证据关联；查阅时用 `auto-iter topic evidence --topic-id <id>`。
15. 安装 AIT 时优先选择操作系统/当前 shell 已认可的命令目录；没有合适目录时只安装到用户目录并提示路径，不默认修改 shell 启动文件。
16. 用户问“之前是不是说过某个现象”这类模糊历史问题时，agent 先运行 `auto-iter search query --text "<用户原话>" --limit 10 --explain`，再用结果中的 path、heading、`run_id`、`decision_id` 或 topic evidence 回到明确证据链。
17. 新 session 恢复时先看 handoff 的 `Current Baseline` 段；该段只作为当前主线入口，细节仍回到 decision、run、artifact、topic evidence 和 plans。
18. 项目根目录 `AGENTS.md` 是可选项目规则文件；handoff 只在该文件已经存在时列入读取顺序，缺失时不创建、不报缺失。
19. 用户要求“更新 AIT”或“update AIT”时，使用 `auto-iter update` 刷新安装产物；默认不运行 `init`，需要检查当前项目状态时显式使用 `--check-project`。
20. 若轻量模糊检索的主观收益不足，再评估是否引入更重的本地 embedding（把文本变成稠密数值向量的模型）或外部服务。
