"""FastMCP サーバーエントリポイント。

起動方法:
    uv run python -m mcp_server.server

Claude Desktop 設定 (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "logi-intel": {
          "command": "uv",
          "args": ["--directory", "/path/to/logi-intel-dashboard",
                   "run", "python", "-m", "mcp_server.server"]
        }
      }
    }
"""
from dotenv import load_dotenv
from fastmcp import FastMCP

from mcp_server.tools.estat_tools import register_tools

load_dotenv()

mcp = FastMCP(
    "logi-intel-dashboard",
    instructions=(
        "日本の物流業界データを分析するツール群。"
        "e-Stat（政府統計）からオープンデータを取得して提供する。"
        "統計表を検索 → メタデータ確認 → データ取得 の3ステップで使う。"
    ),
)

register_tools(mcp)

if __name__ == "__main__":
    mcp.run()
