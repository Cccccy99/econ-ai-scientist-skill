# Econ-AI Scientist Skill

面向 **AI + 经济学** 交叉研究的可复现科研 Skill。将研究问题、变量映射、数据检查、实验规划、统计执行与证据审查连成一条可追溯的工作流。

宿主 AI 负责理论、方法与解释判断；本地 Python 工具负责确定性的检查与统计计算。统计执行无需配置外部模型 API 密钥。

## 能做什么

- 检查 CSV 面板结构、缺失值、数值列和主体—时间重复键，记录输入 SHA-256。
- 创建可审查的研究计划，明确变量、证据类别和执行授权。
- 估计双向固定效应模型，使用主体聚类标准误，比较基准、替代指标与加入控制项三类规格。
- 统一使用共同完整样本，保留不显著结果，生成计划快照、结果、审查清单、报告及文件哈希。
- 指导数据、假设、模型、稳健性、结论五个视角的证据审查，并保留修订记录。

## 快速运行

需要 Python 3.10+。以下命令在本仓库根目录、你选定的 Python 环境中运行：

```sh
python -m pip install -r requirements.txt
python scripts/econ.py demo --out demo-001 --approve
python scripts/econ.py verify --run demo-001/run
```

演示包含 **144 条自建模拟观测、12 个主体、12 个时期**。它验证流程能否运行，不代表真实经济规律或应用成效。`--approve` 仅在用户已经授权具体执行时使用。

只有数据检查时，无需安装统计依赖：

```sh
python scripts/econ.py profile --data assets/demo_panel.csv --entity country --time year
```

将本目录作为 Skill 交给支持 `SKILL.md` 的宿主，入口见 [SKILL.md](SKILL.md)。在魔搭创建页可上传根目录直接含 `SKILL.md` 的 ZIP 包。宿主需支持本地 Python 才能完成统计执行；只读宿主可以使用规划与审查指导。

## 用户数据

先按 CSV 的真实列名确定主体键、时间键与变量映射，再生成计划。例如：

```sh
python scripts/econ.py plan --data data.csv --entity country --time year --x internet --y youth_unemployment --control ln_gdp_pc --control urban --alternative-x mobile --question "互联网普及与青年失业率的关联是什么？" --evidence-class REAL_DATA_EMPIRICAL --out plan-001.json
python scripts/econ.py check --plan plan-001.json
python scripts/econ.py run --plan plan-001.json --out run-001 --approve
```

具体参数、检查门槛和失败处理见 [CLI 说明](references/cli.md)，科学审查见 [五维审查](references/review.md)。不要为显著性反复挑选变量、样本或规格。

## 测试与验证

```sh
python -m unittest discover -s tests -v
```

本地已通过 15 项 CLI 集成测试，覆盖已知系数恢复、共同样本、不显著规格保留、重复键、输入变化、秩不足、授权声明和输出保护；Skill 结构校验与完整演示均通过。验证环境为 Python 3.12.14、numpy 2.5.4、pandas 3.0.5、scipy 1.18.1、statsmodels 0.14.6；其他版本组合需自行验证。

## 解释与授权边界

固定效应和显著性不构成因果识别。确定性审查总体保持 `REVIEW_REQUIRED`，不能代替学科判断；本地脚本不调用五个独立大模型。共同完整样本可能引入选择偏差，少量聚类的推断仍需审查。哈希证明相对于清单的文件一致性，不证明数据来源真实。

本仓库是从原 Econ-AI Scientist 流程抽取的独立能力，包含新写的 Skill、脚本、测试和模拟数据，按 [MIT](LICENSE) 授权。它不包含原应用的服务器、前端或完整多智能体系统，也不改变原始源码与第三方依赖的授权。原项目配合方式见 [项目集成说明](references/project-integration.md)。
