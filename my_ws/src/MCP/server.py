"""
Minimal MCP server with an ADD tool based on fastmcp.

Run:
    python server.py
"""

from fastmcp import FastMCP

# 1) 创建 MCP 实例
mcp = FastMCP("add-server")

# 2) 注册 ADD 工具
@mcp.tool(name="ADD", description="Add two numbers and return the sum.")
def add(a: float, b: float) -> float:
    return a + b

# 3) 启动服务
if __name__ == "__main__":
    mcp.run()
