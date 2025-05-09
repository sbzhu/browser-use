import asyncio
import os
import requests # 用于发送HTTP请求
import json
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pydantic import SecretStr
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

from browser_use import Agent # 假设 browser_use 在您的PYTHONPATH中

# 加载环境变量 (如果需要API密钥等)
load_dotenv()

class MyCustomChatModel(BaseChatModel):
    api_url: str
    api_key: Optional[SecretStr] = None
    model_name: str = "my-custom-model"
    temperature: float = 0.7
    max_tokens: Optional[int] = 1024
    # ... 其他您模型可能需要的参数

    @property
    def _llm_type(self) -> str:
        return "my-custom-chat-model"

    def _convert_messages_to_api_format(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """将LangChain消息转换为您的API所需的格式。"""
        api_messages = []
        for message in messages:
            role = ""
            if isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            elif isinstance(message, ChatMessage):
                role = message.role
            else:
                raise ValueError(f"Unsupported message type: {type(message)}")
            api_messages.append({"role": role, "content": message.content})
        
        # 构建您的API请求体
        # 这只是一个示例，您需要根据您的API文档进行调整
        return {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            # ... 其他API参数
        }

    def _parse_api_response(self, response_data: Dict[str, Any]) -> AIMessage:
        """解析API响应并返回AIMessage。"""
        # 根据您的API响应结构提取内容
        # 这只是一个示例
        try:
            content = response_data["choices"][0]["message"]["content"]
            return AIMessage(content=content)
        except KeyError as e:
            raise ValueError(f"Error parsing API response: {response_data}. Missing key: {e}")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        request_data = self._convert_messages_to_api_format(messages)

        if stop:
            request_data["stop"] = stop # 如果您的API支持stop参数
        
        request_data.update(kwargs)

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.get_secret_value()}" # 或者其他认证方式
        
        print(f"Sending request to {self.api_url} with data: {request_data}")
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=request_data,
                timeout=120 # 设置超时
            )
            response.raise_for_status() # 如果HTTP状态码是4xx或5xx，则抛出异常
            response_data = response.json()
            print(f"Received response: {response_data}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"API request failed: {e}")

        ai_message = self._parse_api_response(response_data)
        return ChatResult(generations=[ChatGeneration(message=ai_message)], llm_output=response_data)

async def run_with_custom_model():
    # 从环境变量或配置文件中获取您的API信息
    custom_api_url = os.getenv("CUSTOM_LLM_API_URL")
    custom_api_key = os.getenv("CUSTOM_LLM_API_KEY")
    custom_model_name = os.getenv("CUSTOM_LLM_MODE_NAME", "default-model")

    if not custom_api_url:
        raise ValueError("MY_CUSTOM_API_URL environment variable not set.")

    llm = MyCustomChatModel(
        api_url=custom_api_url,
        api_key=SecretStr(custom_api_key) if custom_api_key else None,
        model_name=custom_model_name,
        temperature=0.5 # 根据需要调整
    )

    agent = Agent(
        task="Go to example.com and tell me the main heading.",
        llm=llm,
        use_vision=False # 如果您的模型不支持视觉，则设为False
    )

    await agent.run()

if __name__ == "__main__":
    asyncio.run(run_with_custom_model())