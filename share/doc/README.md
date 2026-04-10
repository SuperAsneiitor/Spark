# Spark 文档总览

`Spark` 是面向 StdCell 库自动化生成的流程框架。当前版本已经完成：

- 新版 CLI 命令体系（`create_*_env` / `run_*` / `check_*` / `report_*`）
- `init_env` 项目级初始化（非子模块）
- 统一检查与报告能力（`check_result()` / `extract_report()`）
- 模块子包下沉结构（每个 module 独立目录）

---

## 文档入口

- 用户指导文档：`share/doc/USER_GUIDE.md`
- 开发者文档：`share/doc/DEVELOPER_GUIDE.md`
- 接口级规范：`share/doc/INTERFACE_SPEC.md`
- 演示 Demo：`share/doc/DEMO.md`

---

## 10 秒上手

```bash
pip install -r requirements.txt
python bin/spark -c test_work/proj.yaml init_env
python bin/spark -c test_work/proj.yaml create_analysis_env
python bin/spark -c test_work/proj.yaml run_analysis
python bin/spark -c test_work/proj.yaml check_analysis
python bin/spark -c test_work/proj.yaml report_analysis
```

完整流程和输出说明见 `share/doc/DEMO.md`。
