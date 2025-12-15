import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..state import JarvisState
from ...config.settings import get_settings

logger = logging.getLogger(__name__)

_LLM_INTENT = ChatOpenAI(
    model=get_settings().llm.model.intent,
    api_key=get_settings().llm.get_key,
    base_url=get_settings().llm.host
)

# 定义意图分类的结构化输出模型
class IntentClassification(BaseModel):
    """意图分类结果"""
    intent: str = Field(description="识别出的意图类型")
    confidence: float = Field(description="分类置信度", ge=0, le=1)
    requires_clarification: bool = Field(description="是否需要进一步澄清")
    clarification_question: Optional[str] = Field(description="需要澄清的问题")


class EntityExtraction(BaseModel):
    """实体提取结果"""
    city_name: Optional[str] = Field(description="城市名称")
    device_name: Optional[str] = Field(description="设备名称")
    action: Optional[str] = Field(description="执行动作")
    time_expression: Optional[str] = Field(description="时间表达式")
    location: Optional[str] = Field(description="具体位置")


def create_intent_recognition_system():
    """创建意图识别系统"""

    def recognize_intent(state: JarvisState) -> JarvisState:
        """核心意图识别节点"""

        system_prompt = """你是一个智能家庭助手的意图分类器。你的任务是准确理解用户请求并分类。

        可识别的意图类型包括：
        - `weather_query`: 查询天气、气温、湿度、天气预报等
        - `device_control`: 控制家居设备，如开灯、关空调、调节温度等
        - `schedule_management`: 日程安排、提醒设置、定时任务等
        - `information_query`: 查询家庭信息、设备状态、使用说明等
        - `general_chat`: 问候、闲聊、自我介绍等一般对话
        - `emergency_alert`: 安全警报、紧急情况处理
        - `scene_activation`: 场景模式激活，如"影院模式"、"离家模式"等

        请同时提取请求中的关键实体信息。如果信息不完整需要澄清，请设置requires_clarification为true。"""

        user_prompt = f"用户输入: {state['user_input']}"

        # 使用结构化输出确保结果一致性
        intent_classifier = _LLM_INTENT.with_structured_output(IntentClassification)
        entity_extractor = _LLM_INTENT.with_structured_output(EntityExtraction)

        try:
            # 识别意图
            intent_result = intent_classifier.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])

            # 提取实体
            entity_result = entity_extractor.invoke(user_prompt)
            logger.info(msg="Success to intent classifier")
            return {
                "user_input": user_prompt,
                "primary_intent": intent_result.intent,
                "extracted_entities": {
                    "city_name": entity_result.city_name,
                    "device_name": entity_result.device_name,
                    "action": entity_result.action,
                    "time_expression": entity_result.time_expression,
                    "location": entity_result.location
                },
                "module_data": {
                    "intent_confidence": intent_result.confidence,
                    "requires_clarification": intent_result.requires_clarification,
                    "clarification_question": intent_result.clarification_question
                }
            }

        except Exception as e:
            logger.error(f"Error: {e}")
            # 失败时降级到基于规则的简单分类
            return fallback_intent_classification(state)

    def fallback_intent_classification(state: JarvisState) -> JarvisState:
        logger.warning(msg="Fallback intent classification")
        """降级意图分类策略"""
        user_input = state["user_input"].lower()

        # 关键词映射
        intent_keywords = {
            "weather_query": ["天气", "气温", "温度", "下雨", "下雪", "weather"],
            "device_control": ["打开", "关闭", "调", "开灯", "关灯", "启动", "停止"],
            "schedule_management": ["提醒", "定时", "日程", "闹钟"],
            "general_chat": ["你好", "嗨", "你是谁", "帮助"],
        }

        for intent, keywords in intent_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                return {
                    "primary_intent": intent,
                    "extracted_entities": {},
                    "module_data": {"intent_confidence": 0.7, "requires_clarification": False}
                }

        return {
            "primary_intent": "general_chat",
            "extracted_entities": {},
            "module_data": {"intent_confidence": 0.5, "requires_clarification": True}
        }

    return recognize_intent


# 创建意图识别函数
intent_recognition_node = create_intent_recognition_system()