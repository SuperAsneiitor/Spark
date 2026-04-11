# Spark

StdCell library automation framework built with Python 3.9+, designed to combine EDA flow orchestration with modern software engineering practices.

## Highlights

- Project-level initialization via `init_env`
- Stage command split: `create_*_env`, `run_*`, `check_*`, `report_*`
- Unified stage directories: `run/`, `scr/`, `check/`, `report/`, `release/`
- Config-driven flow with YAML + Jinja2 templates
- Local demo environment under `test_work/`
- Optional internal Fernet decryption for YAML when `SPARK_ENCRYPTED_CONFIG` + `SPARK_FERNET_KEY` are set (see User Guide)
- Optional CLI license gate via `spark_system.yaml` / `SPARK_SYSTEM_CONFIG` (see User Guide)

## Quick Start

```bash
pip install -r requirements.txt
python bin/spark -c test_work/proj.yaml init_env
python bin/spark -c test_work/proj.yaml create_analysis_env
python bin/spark -c test_work/proj.yaml run_analysis
python bin/spark -c test_work/proj.yaml check_analysis
python bin/spark -c test_work/proj.yaml report_analysis
```

## Full Flow

```bash
python bin/spark -c test_work/proj.yaml run_all
python bin/spark -c test_work/proj.yaml run_all --from-stage gen_lib
```

## Documentation

- User Guide: `share/doc/USER_GUIDE.md`
- Developer Guide: `share/doc/DEVELOPER_GUIDE.md`
- Interface Spec: `share/doc/INTERFACE_SPEC.md`
- Demo: `share/doc/DEMO.md`
- Nuitka Linux binary build (standalone / one-folder): `share/doc/NUITKA_BUILD.md`

## License

MIT License. See `LICENSE`.

