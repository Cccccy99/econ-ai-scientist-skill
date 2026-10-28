# 与原 Econ-AI Scientist 项目配合

本 Skill 是从原项目“规划—执行—测试—修订”的思路抽取的独立本地能力，不含整个原始应用、模型权重或其服务器环境，也不承诺复现原有界面、全部智能体及历史实验。

## 已知项目结构与使用顺序

用户提供项目根目录后，先读取该目录实际存在的 AGENTS.md、docs/README.md、docs/CONTEXT.md、docs/WORKFLOW.md 以及相关模块文档。不要把此说明里的历史状态作为当前运行依据。

原项目使用 `project/bin/agent` 分发到 `project/cli/agent_cli.py`，注册 paper、vis、hypothesis、experiment、test、abstract 六个模块，业务入口格式为 `agent <module> <command> <RQNNN> [arguments...]`。先查看帮助、doctor 与 modules；依照实际帮助确认参数。原项目面向服务器环境，Windows 上需要逐项核查依赖、路径和执行器，必要时使用已有 Linux/WSL 环境，不宣称解压即完成部署。

只读核查命令示意（在 project 根目录及正确环境中执行，以实际 --help 为准）：

```sh
python cli/agent_cli.py help
python cli/agent_cli.py doctor --json
python cli/agent_cli.py modules --json
```

历史 RQ 编号与实验结果仅在当前源码或材料中确实存在、且已核验时使用。不要假设任何特定编号可以直接运行。若需获取任务、实验与测试结果，先读对应子命令帮助，再查询。

## 分工与边界

原项目的模型负责科学判断与计划建议，执行器负责文件和计算。不要使用人工写死 PASS 替代审查，不要把自动修复建议当成已经批准的变更。执行、修改计划、重测和确认最终结论应分别核实状态；沿用用户已授予的授权，不重复请求。

本包本地工具固定使用共同完整样本。原项目不同实验如果各自删缺失，样本数可能不同；不可宣称两者数值必然一致。比较前需核对同一输入、变量、样本、方法、协方差设置和版本。

原应用依赖的模型服务或外部数据不可默认为已配置。不要外发 .env、密钥、用户数据、日志中的凭据，也不要默认启动服务器、上传数据或发表论文。原源码本次发现未附独立 LICENSE，因此本 Skill 的 MIT 授权只覆盖包内新写资源，不能替代原项目的授权。
