import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    # 让 client 通过 stdio 启动并连接你的 server.py
    server = StdioServerParameters(
        command="python3",
        args=["/home/hw/arm-1/my_ws/src/MCP/server.py"],
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # 调用 server.py 里的 ADD 工具
            result = await session.call_tool("ADD", {"a": 3, "b": 5})

            # 打印结果
            if result.content:
                print("ADD(3, 5) =", result.content[0].text)
            else:
                print("ADD(3, 5) =", result)


if __name__ == "__main__":
    anyio.run(main)
