"""测试直接导入 scripts/ 下的模块（与流程脚本的运行方式一致）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
