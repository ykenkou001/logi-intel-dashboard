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

from mcp_server.tools.clo_tools import register_tools as register_clo_tools
from mcp_server.tools.corp_number_tools import register_tools as register_corp_tools
from mcp_server.tools.energy_tools import register_tools as register_energy_tools
from mcp_server.tools.estat_tools import register_tools as register_estat_tools
from mcp_server.tools.macro_tools import register_tools as register_macro_tools
from mcp_server.tools.weather_tools import register_tools as register_weather_tools
from mcp_server.tools.xroad_tools import register_tools as register_xroad_tools

load_dotenv()

mcp = FastMCP(
    "logi-intel-dashboard",
    instructions=(
        "日本の物流業界データを分析するツール群。"
        "e-Stat・国税庁・気象庁・エネ庁・xROAD のオープンデータを統合して提供する。"
        "都道府県の物流マクロ概況は logi_macro_overview で一括取得できる。"
        "CLO（物流統括管理者）計画書策定支援は logi_clo_* ツール群を使う。"
    ),
)

register_estat_tools(mcp)
register_weather_tools(mcp)
register_corp_tools(mcp)
register_energy_tools(mcp)
register_xroad_tools(mcp)
register_macro_tools(mcp)
register_clo_tools(mcp)

if __name__ == "__main__":
    mcp.run()
