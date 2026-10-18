# UC 标准化试点库

本仓库保存按 [SJTU 交付要求](https://notes.sjtu.edu.cn/s/zzB-Iq_eRD)整理的派生 UC 试点。原始资料主库为 [UC_datas_codex](https://github.com/djxxju/UC_datas_codex)；本轮不向原库提交，不替换其原件或 Release。这里的 `sources/` 是试点所需原文件的字节一致副本。

## 已交付试点

| 算例 | 规模 | 时间 | 转换身份 | 状态 |
|---|---:|---:|---|---|
| [orlib_10_0_4_w_quad_v1](cases/orlib_10_0_4_w_quad_v1/) | 10 机组 | 24 小时 | 派生，模型有变化 | 格式检查见报告；未求解 |
| [orlib_20_0_1_w_quad_v1](cases/orlib_20_0_1_w_quad_v1/) | 20 机组 | 24 小时 | 派生，模型有变化 | 格式检查见报告；未求解 |

两例各含 `units.json`、`stochastic.json`、`provenance.json` 和 README。机组数组下标从 0 开始，原机组编号映射保存在 provenance。原 `.json.gz` 共享副本在 [sources/or-lib](sources/or-lib/)，完整许可在 [ORLIB_LICENSE.txt](sources/ORLIB_LICENSE.txt)。无需修改原始仓库即可使用此目录。

## 转换中的实质差异

- 源 UC.jl 文件使用分段线性成本。此处以首、中、末节点插值二次式，并检查所有节点；节点吻合不代表区间内费用相同。逐机每段的最大费用差保存于 provenance。两例单机单小时最大绝对差分别约为 **6.678** 和 **9.377** 个原始美元标记单位；这不是总目标误差或求解间隙。
- 源文件没有单独启停容量字段；按固定版本读取器的默认大值，结合 pmax 得到有效有限上限。停机费用缺失显式取零，记录为目标假设。
- 原机组爬坡、最小开停机时间、初始历史、初始出力和负荷数值保留。目标普通爬坡在启停时仍生效，另有末小时禁止停机、末端约束截断等规则；源模型等价性没有认证。
- 源读取器默认允许带罚值的功率失配；此目标接口没有对应字段。两例都标记为 `derived_model_changed`，不能用原参考成本宣称复现成功。
- 费用沿用原件 `$` 单位，未换汇；ISO 币种及价格年份尚未独立确认，因此不做跨币种成本比较。

## 下载与读取

点击 Code → Download ZIP 下载整个新仓库，然后解压。进入某个 `cases/<case_id>` 目录，用 Python 的 `json.load` 分别读取三份 JSON。必须同时查阅 provenance 中的模型差异；单独读取 units 不代表完整理解算例。

```python
import json
from pathlib import Path

case = Path('cases/orlib_10_0_4_w_quad_v1')
units = json.loads((case / 'units.json').read_text(encoding='utf-8'))
scenarios = json.loads((case / 'stochastic.json').read_text(encoding='utf-8'))
provenance = json.loads((case / 'provenance.json').read_text(encoding='utf-8'))
print(units['n_units'], units['horizon'], provenance['classification'])
```

## 检查与复现转换

在本仓库根目录执行；建议使用隔离 Python 环境：

```text
python -m pip install -r requirements.txt
python scripts/build_pilot.py
python scripts/validate.py
python -m unittest discover -s tests -v
```

转换器只读本仓库 `sources/`，在 `cases/` 生成派生文件；不下载资料、不修改来源文件，也不访问原始仓库。校验覆盖 JSON Schema、数组长度、有限数字、容量顺序、初始状态、场景概率、来源/输出哈希等。[验证报告](reports/validation.json)记录各例结果。

容量上界预筛按文档解释进行，忽略部分约束；通过只代表没有被该必要条件排除。原先直观选中的部分小例会在目标启停爬坡解释下失败，见 [候选筛选](reports/candidate_screening.json)。不据此判定原始 UC.jl 模型不可行。

**未运行 COPT/Gurobi，未测试你的实际建模程序读取，未完成可行性/最优性或独立验解，没有本项目基准解。** 后续主求解器为 COPT，Gurobi 为兼容目标。

更多说明：[字段与目标规则](docs/profile.md)、[原始数据保护与版本记录](reports/original_preservation.json)、[来源许可与引用](THIRD_PARTY_NOTICES.md)、[本次工作日志](工作日志/2026-10-18-03.md)。
