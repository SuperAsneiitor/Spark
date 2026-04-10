# Spark 用户指导文档（第一性原理版）

## 1. 先理解目标

StdCell 自动化流程的本质是把“可重复、可检查、可追溯”的工程动作标准化。  
Spark 通过四个固定动作把每个阶段变成确定性流程：

- `create_env`：准备运行环境（目录、脚本、上下文）
- `run`：执行阶段逻辑（外部 EDA 或 Python 内部实现）
- `check`：机器化校验（日志错误 + 期望产出）
- `report`：抽取可读摘要（用于评审与交付）

---

## 2. 你会用到的核心文件

- CLI 入口：`bin/spark`
- 项目配置：`test_work/proj.yaml`（可复制为你的工程配置）
- 示例工程根：`test_work/`
- 模板目录：`share/template/`

---

## 3. 环境准备

```bash
pip install -r requirements.txt
```

如果在 Linux EDA 服务器，建议先加载环境：

```csh
source /path/to/Altas/spark.csh
```

---

## 4. 配置文件最小必需字段

```yaml
project:
  name: my_stdcell
  tech_node: "28nm"
  case_name: my_case
  case_version: v1.0
  pvt: [tt_1p10v_025c]

paths:
  work_dir: /abs/path/to/project_root
  gds_source: /abs/path/to/input.gds
  netlist: /abs/path/to/input.cdl
  lef_source: /abs/path/to/tech.lef

tools:
  calibre: calibre
  liberate: liberate
  innovus: innovus
  abstract: abstract
  tetramax: tmax
```

`work_dir` 是项目根目录，`init_env` 会直接在这里创建 `work/ incoming/ release/ cfg/ run/`。

---

## 5. CLI 使用方式（当前版本）

## 5.1 初始化项目根

```bash
python bin/spark -c test_work/proj.yaml init_env
```

## 5.2 对每个阶段分别操作

以 `gen_spice` 为例：

```bash
python bin/spark -c test_work/proj.yaml create_gen_spice_env
python bin/spark -c test_work/proj.yaml run_gen_spice
python bin/spark -c test_work/proj.yaml check_gen_spice
python bin/spark -c test_work/proj.yaml report_gen_spice
```

> 除 `init_env` 外，所有阶段均支持 `create_*/run_*/check_*/report_*`。

## 5.3 全流程执行

```bash
python bin/spark -c test_work/proj.yaml run_all
python bin/spark -c test_work/proj.yaml run_all --from-stage gen_lib
```

---

## 6. 阶段目录结构（每功能一个目录）

每个阶段位于：`<project_root>/work/<stage>/`

```
run/                 # 运行脚本
run/log/             # 运行日志
scr/                 # 生成脚本（tcl/csh）
check/               # 检查能力目录
check/log/           # 检查日志
check/rpt/           # 检查报告（*_check.rpt）
report/              # 汇总报告（*_summary.rpt）
release/output_file/ # 最终输出
release/extract_result/
```

---

## 7. 常见问题

- 为什么 `init_env` 没有 `create_init_env_env`？
  - 因为 `init_env` 是项目初始化命令，语义上保留单命令。

- `check_*` 失败怎么办？
  - 先看 `work/<stage>/check/rpt/<stage>_check.rpt`，再回看 `run/log/*.log`。

- `report_*` 有什么意义？
  - 把关键错误、告警、产出文件汇总成稳定格式，方便评审、归档和 CI 上传。

- Windows 下符号链接报权限？
  - 这是系统权限限制，流程本身允许跳过该动作；Linux EDA 环境通常正常。

---

## 8. 推荐执行顺序

```bash
python bin/spark -c proj.yaml init_env
python bin/spark -c proj.yaml create_analysis_env
python bin/spark -c proj.yaml run_analysis
python bin/spark -c proj.yaml check_analysis
python bin/spark -c proj.yaml report_analysis
# 其余阶段同理
python bin/spark -c proj.yaml run_all
```

