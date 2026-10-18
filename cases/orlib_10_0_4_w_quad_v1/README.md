# orlib_10_0_4_w_quad_v1

源：or-lib/10_0_4_w；10 台机组，24 个小时。

本例是 `derived_model_changed` 派生试点。三份 JSON 必须配合 provenance 使用；来源原包位于 ../../sources/or-lib，原件未修改。

成本由原分段线性节点重建为二次式，区间内有费用变化；普通爬坡、初末边界与功率失配处理也存在模型差异。完整映射、逐机成本误差与假设见 provenance.json。

已通过的检查见 ../../reports/validation.json；必要条件通过不证明可行。未运行 COPT/Gurobi，未验证目标程序读取，也没有基准解。
