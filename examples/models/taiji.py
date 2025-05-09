import asyncio
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from langchain_deepseek import ChatDeepSeek

from browser_use import Agent

# dotenv
load_dotenv()

import os
import requests
import json
from typing import Any, Dict, List, Optional, Union
from pydantic import SecretStr
from dotenv import load_dotenv

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

from browser_use import Agent

# 加载环境变量
load_dotenv()

class CustomRequestChatModel(BaseChatModel):
    """自定义请求模型，通过HTTP请求调用自定义大模型API"""
    
    api_url: str
    api_key: Optional[SecretStr] = None
    model_name: str = "custom-model"
    temperature: float = 0.7
    max_tokens: Optional[int] = 1024
    timeout: int = 120
    
    @property
    def _llm_type(self) -> str:
        return "custom-request-chat-model"
    
    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """将LangChain消息格式转换为API请求格式"""
        formatted_messages = []
        
        # 检查第一个消息是否是system消息
        if not messages or not isinstance(messages[0], SystemMessage):
            # 如果没有system消息，则添加默认的system消息
            formatted_messages.append({
                "role": "system",
                "content": "你是一个由腾讯开发的有用的人工智能助手，你的名字是“腾讯元宝”，简称“元宝”，你的英文名是“Tencent Yuanbao”，你乐于帮助大家解答问题。"
            })
        
        for message in messages:
            if isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            elif isinstance(message, ChatMessage):
                role = message.role
            else:
                raise ValueError(f"不支持的消息类型: {type(message)}")
            
            # 处理基本消息
            msg_dict = {"role": role}
            
            # 处理内容
            if message.content:
                msg_dict["content"] = message.content
            
            formatted_messages.append(msg_dict)
        
        return {
            "messages": formatted_messages,
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": 1.0,
            "stream": False # 确保流式响应被禁用
            # 根据您的API需要添加其他参数
        }
    
    def _parse_response(self, response: Dict[str, Any]) -> AIMessage:
        """解析API响应为LangChain消息格式"""
        if "choices" not in response:
            raise ValueError(f"API响应格式不正确: {response}")
        
        choice = response["choices"][0]
        message = choice.get("message", {})
        
        content = message.get("content", "")
        
        return AIMessage(content=content)
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """生成聊天完成"""
        request_data = self._convert_messages_to_prompt(messages)
        
        # 添加stop序列（如果提供）
        if stop:
            request_data["stop"] = stop
        
        # 合并任何额外的关键字参数
        request_data.update(kwargs)
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # 添加API密钥（如果提供）
        if self.api_key:
            headers["Authorization"] = f"{self.api_key.get_secret_value()}"

        try:
            print('Input:\n{} | {} | {}'.format(self.api_url, headers, request_data))

            # 移除stream=True参数，因为我们不处理流式响应
            response = requests.post(
                self.api_url,
                headers=headers,
                json=request_data,
                stream=False,
            )
            print(f'output: {response}')
            response.raise_for_status()
            response_data = response.json()
            
            ai_message = self._parse_response(response_data)
            
            return ChatResult(
                generations=[ChatGeneration(message=ai_message)],
                llm_output=response_data
            )
        except Exception as e:
            raise ValueError(f"API请求失败: {str(e)}")

# 使用示例
async def main():
    # 初始化模型
    llm = CustomRequestChatModel(
        api_url="http://taiji-stream-server-online-openapi.turbotke.production.polaris:8080/openapi/chat/completions",
        api_key=SecretStr("7ee10a2a-88b5-4b7b-9548-d48513a25de1"),
        model_name="DeepSeek-V3-Online",
        temperature=1.0,
    )
    
    # 创建带有模型的agent
    agent = Agent(
        task="打开百度搜索苹果中国，进入苹果中国官网查看最新的iPhone 15 Pro型号的售价",
        llm=llm,
        use_vision=False  # 根据您的模型是否支持视觉功能来设置
    )
    
    await agent.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())