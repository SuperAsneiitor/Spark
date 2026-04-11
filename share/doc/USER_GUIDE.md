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
各阶段实际沙箱在 `work/<case_name>/<case_version>/` 下；若 YAML 未写 `case_name`，则与 `project.name` 相同；未写 `case_version` 则为 `v1.0`。

---

## 5. CLI 使用方式（当前版本）

## 5.1 初始化项目根

```bash
python bin/spark -c test_work/proj.yaml init_env
```

## 5.2 对每个阶段分别操作

以 `gen_spice` 为例（`porting_gds` / `porting_lef` 与 `gen_gds` 相同：`create_*_env`、`run_*`、`check_*`、`report_*`）：

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

每个阶段位于：`<project_root>/work/<case_name>/<case_version>/<stage>/`（`case_name` / `case_version` 来自 `project:` 配置，与 `incoming/` 一致）

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
  - 先看 `work/<case>/<version>/<stage>/check/rpt/<stage>_check.rpt`，再回看同阶段下 `run/log/*.log`。

- `report_*` 有什么意义？
  - 把关键错误、告警、产出文件汇总成稳定格式，方便评审、归档和 CI 上传。

- Windows 下符号链接报权限？
  - 这是系统权限限制，流程本身允许跳过该动作；Linux EDA 环境通常正常。

---

## 8. License / 账号授权（系统配置）

与项目 `proj.yaml` 独立，使用安装根目录下的 **`spark_system.yaml`**（或通过环境变量 **`SPARK_SYSTEM_CONFIG`** 指定路径，可为绝对路径或相对 SPARK 根目录）。

```yaml
license_check:
  enabled: false          # true 时每次 spark 命令执行前检查
  allowed_users: []       # 与 Linux ``whoami`` 输出一致的用户名
  # allowed_users_file: share/license_allowlist.txt  # 可选，每行一名
```

- 检查在 **`bin/spark` 解析子命令之后、加载 `-c` 项目配置之前**执行。
- **二次开发**：实现 `lib.core.license_guard.LicenseAllowlistProvider`，调用 `set_license_allowlist_provider()` 可接入 LDAP/数据库等（优先于 YAML 名单）。

---

## 9. 加密配置文件（部署侧，无独立对外命令）

框架在内部使用 Fernet（`cryptography`，见 `requirements.txt`）解密配置：**不提供** `spark_crypto` 等对外 CLI。

若 `-c` 指向的文件为密文，由部署环境同时设置：

- `SPARK_ENCRYPTED_CONFIG=1`（或 `true` / `yes` / `on`）
- `SPARK_FERNET_KEY=<Fernet 密钥，与离线加密时一致>`

仍使用常规命令，例如：`python bin/spark -c proj.yaml.enc init_env`。  
离线如何生成密文与密钥由团队自行脚本完成（勿将密钥写入仓库）。

---

## 10. 推荐执行顺序

```bash
python bin/spark -c proj.yaml init_env
python bin/spark -c proj.yaml create_analysis_env
python bin/spark -c proj.yaml run_analysis
python bin/spark -c proj.yaml check_analysis
python bin/spark -c proj.yaml report_analysis
# 其余阶段同理
python bin/spark -c proj.yaml run_all
```

