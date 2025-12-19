# 定义状态，继承MessagesState以自动管理消息历史
import datetime
import logging

from langchain_openai import ChatOpenAI
from langgraph.constants import END
from langgraph.graph import StateGraph

from src.agents.intent.jarvis import intent_recognition_node
from src.agents.mcp_client import get_mcp_tools, life_mcp_manager
from src.agents.state import JarvisState
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_LLM_INTENT = ChatOpenAI(
    model=get_settings().llm.model.intent,
    api_key=get_settings().llm.get_key,
    base_url=get_settings().llm.host
)

_LLM_TOOL_CALLING = ChatOpenAI(
    model=get_settings().llm.model.intent,
    api_key=get_settings().llm.get_key,
    base_url=get_settings().llm.host,
    temperature=0  # 确定性输出，适合工具调用场景
)

def create_router():
    """创建动态路由系统"""

    def route_based_on_intent(state: JarvisState) -> str:
        """根据意图决定下一步执行哪个工作流"""

        intent = state.get("primary_intent", "general_chat")
        requires_clarification = state.get("module_data", {}).get("requires_clarification", False)

        if requires_clarification:
            return "clarification_workflow"

        routing_map = {
            "device_control": "device_control_workflow",
            "schedule_management": "schedule_workflow",
            "information_query": "information_workflow",
            "emergency_alert": "emergency_workflow",
            "scene_activation": "scene_workflow",
            "general_chat": "general_chat_workflow"
        }

        return routing_map.get(intent, "general_chat_workflow")

    return route_based_on_intent


# 创建路由函数
dynamic_router = create_router()


def create_jarvis_workflow():
    """天气查询工作流（您之前实现的升级版）"""

    async def jarvis_workflow(state: JarvisState) -> JarvisState:
        #【关键】动态获取并转换工具
        tools = await get_mcp_tools(life_mcp_manager)
        logger.info(f"🔧 Loaded {len(tools)} tools from MCP Server")

        # 使用之前实现的天气查询逻辑，但集成到新状态结构中
        city_name = state["extracted_entities"].get("city_name") or "东莞"

        # 这里调用您之前实现的MCP工具集成
        # lookup_city -> 智能选择 -> get_weather_now

        weather_data = {
            "city": city_name,
            "temperature": "25°C",
            "condition": "晴朗",
            "humidity": "60%"
        }

        return {
            "module_data": {"weather": weather_data},
            "assistant_response": f"🌤️ {city_name}当前天气：{weather_data['condition']}，温度{weather_data['temperature']}，湿度{weather_data['humidity']}。"
        }

    return jarvis_workflow


def create_device_control_workflow():
    """设备控制工作流示例"""

    def device_control_workflow(state: JarvisState) -> JarvisState:
        device_name = state["extracted_entities"].get("device_name", "")
        action = state["extracted_entities"].get("action", "")

        # 模拟设备控制逻辑
        if device_name and action:
            response = f"✅ 已{action}{device_name}。"
        else:
            response = "请告诉我您想控制哪个设备，执行什么操作？"

        return {
            "module_data": {"device_control": {"device": device_name, "action": action}},
            "assistant_response": response
        }

    return device_control_workflow


def create_general_chat_workflow():
    """通用对话工作流"""

    def general_chat_workflow(state: JarvisState) -> JarvisState:
        user_input = state["user_input"]

        # 简单的对话逻辑，可以替换为更复杂的LLM调用
        responses = {
            "你好": "您好！我是您的家庭助手，可以帮您查询天气、控制设备、管理日程等。",
            "你是谁": "我是您的智能家庭助手，专注于家居环境管理和生活便利服务。",
            "谢谢": "不客气！随时为您服务。"
        }

        response = responses.get(user_input, "我理解您的意思，但还在学习如何更好地为您服务。")

        return {"assistant_response": response}

    return general_chat_workflow


def create_clarification_workflow():
    """信息澄清工作流"""

    def clarification_workflow(state: JarvisState) -> JarvisState:
        question = state.get("module_data", {}).get("clarification_question",
                                                    "请提供更多详细信息以便我更好地帮助您。")

        return {
            "assistant_response": question,
            "module_data": {"awaiting_clarification": True}
        }

    return clarification_workflow


def create_smart_home_assistant():
    """创建完整的家庭助手工作流"""

    workflow = StateGraph(JarvisState)

    # 添加节点
    workflow.add_node("intent_recognition", intent_recognition_node)
    workflow.add_node("weather_workflow", create_jarvis_workflow())
    workflow.add_node("device_control_workflow", create_device_control_workflow())
    workflow.add_node("general_chat_workflow", create_general_chat_workflow())
    workflow.add_node("clarification_workflow", create_clarification_workflow())

    # 设置入口点
    workflow.set_entry_point("intent_recognition")

    # 添加条件路由
    workflow.add_conditional_edges(
        "intent_recognition",
        dynamic_router,
        {
            "weather_workflow": "weather_workflow",
            "device_control_workflow": "device_control_workflow",
            "general_chat_workflow": "general_chat_workflow",
            "clarification_workflow": "clarification_workflow"
        }
    )

    # 添加直接边（各工作流执行后结束）
    workflow.add_edge("weather_workflow", END)
    workflow.add_edge("device_control_workflow", END)
    workflow.add_edge("general_chat_workflow", END)
    workflow.add_edge("clarification_workflow", END)

    return workflow.compile()


# 创建助手实例
smart_home_assistant = create_smart_home_assistant()


async def assistant():
    """测试家庭助手的多功能能力"""

    test_cases = [
        "东莞今天天气怎么样？",
        "打开客厅的灯",
        "你是谁？",
        "设置晚上8点的提醒",
        "帮我关空调"
    ]

    for query in test_cases:
        print(f"\n🧪 用户查询: '{query}'")

        initial_state = {
            "user_input": query,
            "primary_intent": "",
            "extracted_entities": {},
            "conversation_history": [],
            "module_data": {},
            "assistant_response": "",
            "active_workflow": None,
            "error": None,
            "timestamp": datetime.time
        }

        try:
            result = await smart_home_assistant.ainvoke(initial_state)
            print(f"🤖 助手回复: {result['assistant_response']}")
            print(f"📊 识别意图: {result['primary_intent']}")

        except Exception as e:
            print(f"❌ 处理失败: {e}")



import asyncio

asyncio.run(assistant())
