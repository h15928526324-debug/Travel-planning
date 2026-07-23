"""
智行规划师 — 部署入口

Streamlit Cloud / HuggingFace Spaces 要求入口在仓库根目录。
此文件将执行转发到 frontend/app.py。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 读取并执行前端主文件
frontend = PROJECT_ROOT / "frontend" / "app.py"
code = compile(frontend.read_text(encoding="utf-8"), str(frontend), "exec")
exec(code, {"__name__": "__main__"})
