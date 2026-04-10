"""
lib/core/template_engine.py
封装 Jinja2 模板渲染逻辑，剥离 Python 代码与 TCL/CSH 脚本文本。

设计要点：
  - 模板搜索路径默认为 share/template/（相对于 SPARK_HOME）
  - 支持自定义 undefined 策略（StrictUndefined 防止静默错误）
  - 对 TCL/CSH 等含有 $ 符号的模板，使用 {# #} 注释和 {{ }} 变量块，
    避免与 Shell 变量扩展冲突
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound


def _get_default_template_dir() -> Path:
    """推断 share/template 路径：优先读取 SPARK_TMPL 环境变量，否则按相对位置定位。"""
    env_path = os.environ.get("SPARK_TMPL")
    if env_path:
        return Path(env_path)
    # 本文件位于 lib/core/，向上两级到项目根，再拼接 share/template
    return Path(__file__).resolve().parent.parent.parent / "share" / "template"


def _build_env(template_dir: Path) -> Environment:
    """构建 Jinja2 Environment，启用严格 Undefined 策略。"""
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,    # 去除块标签后的换行，保持输出整洁
        lstrip_blocks=True,  # 去除块标签前的空白
        keep_trailing_newline=True,
    )


def render_template(
    template_name: str,
    output_path: Path,
    template_dir: Path | None = None,
    **context: Any,
) -> Path:
    """
    渲染指定 Jinja2 模板并写入目标文件。

    Args:
        template_name: 模板文件名（相对于 template_dir），如 "csh_wrapper.j2"
        output_path:   渲染结果的输出路径
        template_dir:  模板搜索目录，默认使用 share/template
        **context:     传入模板的变量字典

    Returns:
        实际写入的文件 Path 对象

    Raises:
        TemplateNotFound: 模板文件不存在
        jinja2.UndefinedError: 模板中引用了未传入的变量
    """
    tpl_dir = template_dir or _get_default_template_dir()
    env = _build_env(tpl_dir)

    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        raise TemplateNotFound(
            f"找不到模板文件 '{template_name}'，搜索目录: {tpl_dir}"
        )

    rendered = template.render(**context)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    return output_path


def render_string(template_str: str, **context: Any) -> str:
    """
    直接渲染一段 Jinja2 模板字符串（无需模板文件，适合小型动态片段）。

    Args:
        template_str: Jinja2 模板字符串
        **context:    传入模板的变量

    Returns:
        渲染后的字符串
    """
    env = Environment(undefined=StrictUndefined)
    return env.from_string(template_str).render(**context)
