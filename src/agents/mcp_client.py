import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any, List

from langchain_core.tools import StructuredTool
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from pydantic import create_model

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class McpClientManager:
    """
    企业级 MCP 连接管理器 (Singleton)
    负责维护 SSE 长连接，防止每次请求都重新握手
    """
    def __init__(self, sse_url: str):
        self.sse_url = sse_url
        self.session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()

    async def connect(self):
        logger.info(f"🔌 Connecting to MCP Server: {self.sse_url}...")
        try:
            sse_transport = await self._exit_stack.enter_async_context(
                sse_client(self.sse_url)
            )
            self.read, self.write = sse_transport
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(self.read, self.write)
            )
            await self.session.initialize()
            logger.info("✅ MCP Connected.")
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            raise

    async def ensure_connected(self):
        """Helper: 如果没连接，就自动连上"""
        if not self.session:
            logger.warning("⚠️ Session not found, initializing auto-connect...")
            await self.connect()

    async def close(self):
        await self._exit_stack.aclose()

# 全局单例 (实际项目中建议使用依赖注入)
life_mcp_manager = McpClientManager(sse_url=get_settings().mcp_life.get_sse_url())

async def get_mcp_tools(mcp_manager: McpClientManager) -> List[StructuredTool]:
    """
    【核心适配器】
    从远程 MCP Server 获取工具列表，并转换为 LangChain 工具对象
    """
    # 1. 自动检查连接状态
    await mcp_manager.ensure_connected()

    if not mcp_manager.session:
        logger.error("MCP(life_mcp_service) Session not initialized")
        raise RuntimeError("MCP Session not initialized")

    # 1. 远程获取工具定义 (ListTools)
    result = await mcp_manager.session.list_tools()
    lc_tools = []

    for tool_def in result.tools:
        # 2. 动态构建 Pydantic 参数模型
        # 简化处理：将所有参数设为 Any，生产环境应递归解析 JSON Schema
        fields = {
            k: (Any, ...)
            for k in tool_def.inputSchema.get("properties", {}).keys()
        }
        args_schema = create_model(f"{tool_def.name}Schema", **fields)

        # 3. 定义执行闭包 (Capture tool_name)
        async def _executor(tool_name=tool_def.name, **kwargs):
            logger.info(f"   🌐 Calling Remote MCP: {tool_name} {kwargs}")
            try:
                res = await mcp_manager.session.call_tool(tool_name, kwargs)
                # 提取文本结果
                return "\n".join([c.text for c in res.content if c.type == 'text'])
            except Exception as e:
                return f"MCP Tool Error: {str(e)}"

        # 4. 封装为 LangChain Tool
        lc_tools.append(StructuredTool.from_function(
            coroutine=_executor,
            name=tool_def.name,
            description=tool_def.description,
            args_schema=args_schema
        ))

    return lc_tools