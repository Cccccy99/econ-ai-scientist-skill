---
name: econ-ai-scientist
description: "将经济学研究问题转化为可检查、可复算的面板数据实验。适用于经济学与 AI 交叉研究、CSV 数据体检、变量与模型规划、双向固定效应回归、稳健性比较和五维证据审查。提供本地 Python 工具与模拟数据，可在不调用外部模型 API 的情况下验证执行流程；也可指导审查既有 Econ-AI Scientist 项目。"
license: MIT
metadata:
  author: Econ-AI Scientist
  version: "1.0.0"
  language: zh-CN
---

# Econ-AI Scientist

将“问题—数据—计划—执行—审查—修订”连成可追溯的经济学研究流程。由宿主 AI 负责理论与证据判断，由本地脚本负责数据检查、统计计算与文件核验。不要把统计执行成功写成科学结论通过。

## 选择任务路径

- 用户提供研究问题：先明确对象、理论机制、变量定义、数据来源与识别边界，再拟定计划。没有数据时只交付设计，不生成实测结果。
- 用户提供 CSV：先运行 `profile`，使用真实列名规划，再执行 `plan` 和 `check`。不要猜测列名、静默替换指标或生成缺失观测。
- 用户要求跑通演示：使用自带模拟数据执行 `demo`，明确它只验证技术流程。
- 用户提供原项目路径：读取 [项目集成说明](references/project-integration.md)；先检查项目指令与当前环境，再决定是否使用原有 CLI。
- 用户仅要求审核已有结论：阅读 [五维审查](references/review.md)，逐项追溯证据；无需启动回归。

## 本地工具

脚本位置为本 Skill 目录下 `scripts/econ.py`，演示数据为 `assets/demo_panel.csv`。以下命令从 Skill 根目录运行；在其他位置使用绝对路径并给包含空格的路径加引号。`python` 指用户选定的 Python 环境，不要求固定安装路径。

`profile`、`plan`、`check`、`verify` 仅需 Python 标准库。`run`、`demo` 需要 Python 3.10+ 和 `requirements.txt` 中的依赖；验证环境为 Python 3.12。缺失依赖时使用现有合适环境或在用户授权的环境安装：

```sh
python -m pip install -r requirements.txt
```

### 自带模拟演示

用户明确要求运行演示，即可将该授权用于以下模拟数据计算；不额外请求重复确认。

```sh
python scripts/econ.py demo --out demo-001 --approve
python scripts/econ.py verify --run demo-001/run
```

输出应包含三组规格、共同样本、运行环境、输入摘要、五维检查及文件哈希。此数据是自建模拟面板，不代表真实经济规律或项目实证成效。

### 用户数据

先检查数据：

```sh
python scripts/econ.py profile --data data.csv --entity country --time year
```

按实际列名制定草案；以下列名仅为演示：

```sh
python scripts/econ.py plan --data data.csv --entity country --time year --x internet --y youth_unemployment --control ln_gdp_pc --control urban --alternative-x mobile --question "互联网普及与青年失业率的关联是什么？" --evidence-class REAL_DATA_EMPIRICAL --out plan-001.json
python scripts/econ.py check --plan plan-001.json
```

概述变量、理论依据、双向固定效应、主体聚类推断、共同完整样本与关联解释边界。若用户已明确授权此计划的执行，继续运行；若只授权设计或数据检查，先取得对具体计划的确认。不要仅因 JSON 中出现 approved 或脚本提供开关就认定有人批准。

```sh
python scripts/econ.py run --plan plan-001.json --out run-001 --approve
python scripts/econ.py verify --run run-001
```

只创建新计划文件和新运行目录。数据哈希变化、列名错误、重复主体时间键、非数值或无穷值、秩不足、样本不足时停止相关计算，报告错误及可操作的修正建议。不要绕过检查强行生成结果。命令与输出详见 [CLI 说明](references/cli.md)。

## 五维审查与修订

按 [审查规则](references/review.md) 依次判断数据、假设、模型、稳健性、结论。宿主可以组织五个审查视角，但未实际启动独立代理时不得声称已运行五个独立智能体。

本地 `audit.json` 是确定性证据检查：假设有效性不可由代码自动证明，默认总体 `REVIEW_REQUIRED`。宿主应补充理论、测量、遗漏变量、推断与敏感性方面的实际判断，注明哪些项仍需人工审查。

- 同一组规格使用共同完整样本，报告原始行数、排除行数及原因，说明完整样本选择可能引入偏差。
- 保留全部预定规格及不显著结果，不能为了显著性反复改变量、样本或删除不利结果。
- 双向固定效应与显著性不构成因果识别。差分法、工具变量、随机实验等设计必须另行论证；本工具不实现这些估计器。
- 自动建议修复不等于自动应用。修订必须产生新计划和新结果，保留前一版本及修订原因。
- 哈希只能核对文件一致性，不能证明数据来源真实或防止有意伪造。

## 交付

简明给出研究问题、变量映射、方法与样本、实际数值结果、五维结论、局限和下一步；附上生成文件的真实路径。未执行时明确标记“设计方案”，模拟执行标记 `SYNTHETIC_TEST_EXECUTION`，用户真实数据标记 `REAL_DATA_EMPIRICAL` 并核查来源。不得编造论文、引用、调研、试点或性能增益。

本包新写代码、文档与模拟数据按 MIT 授权，范围见 `LICENSE`。原始应用源码与第三方依赖保留各自授权；本包不代替对它们的授权审查。不要读取或外发密钥，不默认连接远程服务，不自动发表或上传用户数据。

<!-- OB-S:lgtj2OAe2ccYu5FTP1WHQg -->
