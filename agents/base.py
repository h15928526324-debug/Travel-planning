"""
Agent 基类 — 封装 LLM 调用、工具绑定、结构化输出
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool

from config.settings import get_settings, get_effective_llm_config, has_user_api_config


def create_llm(temperature: float = 0.7, model: str | None = None) -> ChatOpenAI:
    """
    工厂函数：创建 LLM 实例。

    优先级: 用户自己配置的 API Key > 全局 .env 配置
    当两者都缺失时给出明确的中文提示。
    """
    cfg = get_effective_llm_config()

    if not cfg["api_key"]:
        from config.settings import PROJECT_ROOT
        raise RuntimeError(
            "\n❌ 未检测到 API Key，无法调用大模型。\n\n"
            "请选择一种方式配置:\n\n"
            "  🔑 个人配置 (推荐): 在页面左侧「🔑 API 设置」中填入你的 Key\n"
            f"  🌐 全局配置: 编辑 {PROJECT_ROOT / '.env'} 文件\n\n"
            "支持 OpenAI / DeepSeek / 及其他兼容接口的 API Key"
        )

    return ChatOpenAI(
        model=model or cfg["model"],
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        temperature=temperature,
        max_tokens=4096,
        request_timeout=120,
        max_retries=2,
    )


class BaseAgent(ABC):
    """
    Agent 基类

    每个子类需要定义:
      - name: Agent 名称
      - role: 角色描述
      - system_prompt: 系统提示词
      - tools: 可用工具列表
    """

    name: str = "base"
    role: str = "通用助手"
    system_prompt: str = "你是一个旅行规划助手。"
    tools: list[BaseTool] = []
    llm: ChatOpenAI | None = None
    temperature: float = 0.7

    def __init__(self, temperature: float | None = None):
        if temperature is not None:
            self.temperature = temperature
        self.llm = create_llm(temperature=self.temperature)

    def _build_messages(self, user_message: str, context: str = "") -> list:
        """构建消息列表"""
        prompt = self.system_prompt
        if context:
            prompt += f"\n\n## 当前上下文信息\n{context}"

        return [
            SystemMessage(content=prompt),
            HumanMessage(content=user_message),
        ]

    @abstractmethod
    def invoke(self, state: dict) -> dict:
        """
        执行 Agent 推理。

        Args:
            state: LangGraph 当前状态

        Returns:
            状态更新字典 (partial state update)
        """
        ...

    def _call_llm(self, user_message: str, context: str = "") -> str:
        """基础 LLM 调用"""
        messages = self._build_messages(user_message, context)
        response = self.llm.invoke(messages)
        return response.content

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} role={self.role}>"
