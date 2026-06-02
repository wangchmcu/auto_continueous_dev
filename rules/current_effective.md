# Current Effective Rules

## AIT changes require old project migration check

- rule_id: RL-b6469b812f
- source_kind: user_stated
- rule_kind: acceptance
- scope_kind: global

每次完成 AIT 功能或文档改动后，结束前必须检查旧项目如何迁移：至少确认 README、AGENTS、skills 和 plan 是否说明旧项目迁移路径，并按变更风险运行或更新 auto-iter migrate、auto-iter update --check-project、auto-iter handoff validate 相关测试；不能只验证新项目路径。
