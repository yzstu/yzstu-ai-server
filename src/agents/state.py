from typing import Dict, Optional, Any

from langgraph.graph import MessagesState


class JarvisState(MessagesState):
    """增强的家庭助手状态结构，支持多意图和多任务上下文"""

    # 用户原始输入
    user_input: str
    # 识别出的主导意图
    primary_intent: str
    # 从用户输入中提取的实体（如城市名、设备名、时间等）
    extracted_entities: Dict[str, Any]
    # 对话历史
    # conversation_history: Annotated[List[Dict], operator.add]
    # 各功能模块的中间结果
    module_data: Dict[str, Any]
    # 助手最终响应
    assistant_response: str
    # 当前活跃的子工作流（用于复杂任务）
    active_workflow: Optional[str]
    # 错误信息
    error: Optional[str]
    # 时间戳
    timestamp: str