# Spark 演示 Demo（可直接复现）

本 Demo 基于仓库内置 `test_work/proj.yaml`，不依赖真实 EDA 工具（配置中工具路径为 `echo`）。

---

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

---

## 2. 查看命令帮助

```bash
python bin/spark -h
```

你应看到以下命令形态：

- `init_env`
- `create_<stage>_env`
- `run_<stage>`
- `check_<stage>`
- `report_<stage>`
- `run_all`

---

## 3. 初始化项目环境

```bash
python bin/spark -c test_work/proj.yaml init_env
```

关键输出目录（位于 `test_work/`）：

- `work/`
- `incoming/`
- `cfg/proj_demo.yaml`
- `run/run_flow.csh`

---

## 4. 演示单阶段闭环（analysis）

```bash
python bin/spark -c test_work/proj.yaml create_analysis_env
python bin/spark -c test_work/proj.yaml run_analysis
python bin/spark -c test_work/proj.yaml check_analysis
python bin/spark -c test_work/proj.yaml report_analysis
```

检查以下文件是否生成：

- `test_work/work/fake_stdcell/v1.0/analysis/run/run_analysis.csh`
- `test_work/work/fake_stdcell/v1.0/analysis/report/analysis_report.txt`
- `test_work/work/fake_stdcell/v1.0/analysis/report/target_list.txt`
- `test_work/work/fake_stdcell/v1.0/analysis/check/rpt/analysis_check.rpt`
- `test_work/work/fake_stdcell/v1.0/analysis/report/analysis_summary.rpt`

---

## 5. 演示全流程

```bash
python bin/spark -c test_work/proj.yaml run_all
```

从中间阶段继续：

```bash
python bin/spark -c test_work/proj.yaml run_all --from-stage gen_lib
```

---

## 6. 你将看到的目录结构（示例）

`test_work/work/fake_stdcell/v1.0/analysis/`（`proj.yaml` 中 `case_name` / `case_version`）：

```
run/
run/log/
scr/
check/
check/log/
check/rpt/
report/
release/output_file/
release/extract_result/
```

---

## 7. 故障定位最短路径

- 执行失败：优先看 `work/<case>/<version>/<stage>/run/log/*.log`
- 校验失败：看 `work/<case>/<version>/<stage>/check/rpt/<stage>_check.rpt`
- 报告异常：看 `work/<case>/<version>/<stage>/report/<stage>_summary.rpt`

---

## 8. 一键重建测试环境（可选）

```bash
python test_work/bootstrap.py
```

该脚本会按顺序为各阶段执行 `create_env`，并对 `analysis` 额外执行 `run()`，适合快速验证目录和模板渲染是否健康。

