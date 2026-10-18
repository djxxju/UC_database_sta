# sjtu-hourly-uc/0.1.0 字段与验收说明

参考：[交付机组数据要求](https://notes.sjtu.edu.cn/s/zzB-Iq_eRD)，读取日期 2026-10-18。页面版本信息见 [reference_versions.json](../reports/reference_versions.json)。本规范为该文档的试点实现，实际求解程序源码尚未提供。

每例提供 units.json、stochastic.json、provenance.json、README；原件位于仓库共享 sources/ 路径，provenance 给出相对地址、官方 URL 和 SHA-256。完整下载仓库即可获得原件及派生数据；旧原库不参与转换写操作。

## units.json

| 字段 | 类型、长度 | 语义 |
|---|---|---|
| n_units、horizon | 正整数 | 机组数、小时数；步长固定 1 小时 |
| base_load | 非负数数组，horizon | 系统负荷，MW |
| pmin、pmax | 非负数数组，n_units | 在线最小/最大功率，MW |
| pstart、pshut | 非负数数组，n_units | 启动小时、停机前小时的出力加备用容量上限，MW，均不超过 pmax |
| ramp_up、ramp_down | 非负数数组，n_units | 相邻小时出力变化上限，MW/时段；此处时段为 1 小时 |
| min_up、min_down | 整数数组，n_units，至少 1 | 最小连续开/停机小时 |
| initial_duration | 数值数组，n_units | 正为连续在线小时，非正按目标解释为停机；本试点来源不接受零或缺失历史 |
| initial_output | 非负数数组，n_units | 初始实际出力 MW；参考可省略，本仓库试点要求显式提供 |
| cost_a、cost_b、cost_c | 非负数数组，n_units | a·p²+b·p+c·u，分别为二次、一次、空载费用；按小时计算，不重复加固定项 |
| startup_cost、shutdown_cost | 非负数数组，n_units | 每次启动、停机费用 |
| cold_startup_cost、cold_start_hours | 可选，必须成对 | 费用非负且不低于热启动费；小时为非负整数 |

所有数值有限，禁止 NaN/Infinity/null/带单位字符串。所有机组数组顺序相同，provenance.unit_mapping 使用从 0 开始的下标。停机初始出力为零；在线初始出力处于 [pmin,pmax]。币种单位见 provenance，不无依据换汇。

## stochastic.json

reserve_fraction 为非负标量。scenarios 至少一个，每个 name 非空且唯一，probability 为正、概率和与 1 的误差不超过 1e-9。场景使用 load_factor 或 load 恰好一个；负荷为非负数，完整曲线长度必须为 horizon。

本批仅提供确定性 base 场景、概率 1、load_factor=1 和零备用；不自行生成随机负荷，不把源逐时备用改成近似比例。

## 目标规则与差异记录

目标按文档采用全天共用启停、分场景出力和备用；普通爬坡也作用于启停；冷启动触发为连续停机时长严格大于 min_down+cold_start_hours；末小时禁止停机，末端最小开停机约束截断。试点没有冷热双档输入；校验器检查可选字段配对及数值关系，不构造冷启动调度。

本接口不包含网络、储能、水量、故障、时变可用容量或灵活弃风弃光模块。转换器遇到本批以外源结构直接报错，避免静默丢弃约束。结构规范与模型语义分开验收：通过结构不证明模型等价、可行或最优。

## 成本转换与误差

将源 PWL 首/中/末点插值为二次式，40 位 Decimal 运算后导出有限浮点数；全部源节点残差须不超过 1e-7，且所有目标系数非负，否则拒绝。该容差只用于节点一致性，不能作为 PWL 到二次式的全区间误差容差。

对每段线性源函数与目标二次式之差，检查端点以及导数为零的区间内点，记录最大绝对费用变化和发生功率。没有把该变化当成可接受的生产级误差阈值，更没有据此估计总调度成本差。两例始终标记 derived_model_changed。

## 版本与状态

- 格式：sjtu-hourly-uc/0.1.0。
- 转换器：pilot-converter/0.1.0，代码哈希随每例记录。
- 校验：JSON Schema Draft 2020-12 + Python 跨字段检查 + 来源/输出哈希 + 必要条件上界预筛。
- 目标程序导入：not_tested；求解：not_run；独立验解：not_run。
- 上游参考结果不移作本项目基准解。
