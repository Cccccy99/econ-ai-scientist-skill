# 本地命令与结果

命令从 Skill 根目录运行。所有命令通过标准输出返回 JSON；成功退出码为 0，检查阻塞为 2。参数用操作系统的参数数组或安全引用传递；不要把用户列名、问题或路径拼入 shell 表达式。

## 命令

| 命令 | 参数 | 用途 |
|---|---|---|
| profile | --data CSV --entity 列 --time 列 [--out JSON] | 输入 SHA-256、行数、主体数、时期数、缺失与有限数值计数、重复键 |
| plan | 同上，另加 --x 列 --y 列 --question 文本 --evidence-class 类别 --out 新JSON | 生成待审查草案 |
| plan 可选参数 | --control 列（可重复） --alternative-x 列 | 声明控制项与替代解释变量 |
| check | --plan JSON | 不估计模型，验证草案的数据约束 |
| run | --plan JSON --out 新目录 --approve | 在已有用户授权下执行预定规格 |
| demo | --out 新目录 --approve | 执行随包模拟示例 |
| verify | --run 运行目录 | 核对结果文件与清单的哈希 |

证据类别只接受 `SYNTHETIC_TEST_EXECUTION` 和 `REAL_DATA_EMPIRICAL`。类别由使用者声明，代码无法确认文件是否真为真实数据。`--approve` 也是执行授权的声明，不是人类审批的独立证明。

## 估计约定

CSV 使用 UTF-8（允许 BOM），首行列名唯一、非空且无首尾空格。时间键为有限整数；主体键不为空，主体与时间组合唯一。缺失标记为大小写不敏感的空字符串、na、n/a、nan、null、none；无穷值不作为缺失值自动删除。

依次估计基准 X、可选替代 X、可选加入控制项的 X。三者均加入主体与时间固定效应；使用 statsmodels OLS 的主体聚类协方差及 t 分布推断。共同完整样本由 Y、X、全部控制项和替代 X 的并集决定。至少 5 个主体、2 个时期、正残差自由度与满列秩是机械门槛，不能作为统计功效充足或聚类推断可靠的证明。尤其在少量聚类时需要进一步评估。

本地工具不自动填补缺失、不自动寻找显著模型、不计算因果效应、不训练大模型，也不访问任何模型 API。高维大型面板的内存与计算量需要另行评估；当前使用显式固定效应虚拟变量。

## 每次运行的六个文件

| 文件 | 内容 |
|---|---|
| plan.snapshot.json | 执行计划快照 |
| profile.json | 输入数据检查及摘要 |
| results.json | 所有模型、样本、系数、标准误、p 值、95% 区间及环境版本 |
| audit.json | 五维机械证据状态与人工待审项 |
| report.md | 可读执行报告 |
| manifest.json | 前五个文件的 SHA-256 |

新目录保留版本，不覆盖已存在的计划或非空运行目录。`demo` 另生成根目录的 `plan.json`，运行结果在其 `run/` 中。哈希核验只证明相对于当前清单的一致性，清单本身没有数字签名，不能作为来源真实性或防伪证明。

## 常见阻塞

`UNKNOWN_COLUMN`：核对真实列名，明确映射后建新计划。

`DUPLICATE_PANEL_KEYS`：定位重复原因，向用户提出合并或筛选规则，不静默去重。

`INPUT_CHANGED`：输入发生变化；生成新计划并重新审查。

`APPROVAL_REQUIRED`：尚未声明对具体执行的授权；已有明确授权时使用 --approve。

`MISSING_DEPENDENCY`：选择有依赖的 Python 环境，或按 requirements.txt 安装。

`RANK_DEFICIENT` / `INSUFFICIENT_DF` / `INSUFFICIENT_PANEL`：报告模型或样本约束，不自动删除用户指定变量。

`OUTPUT_EXISTS`：选择新修订路径；保留旧结果。

`ARTIFACT_CHANGED`：检查文件是否缺失或变动，禁止把未通过核验的材料当作已核验结果。
