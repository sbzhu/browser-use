import asyncio
import os

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr
from browser_use import Agent, Browser, BrowserConfig

from browser_use import Agent

# dotenv
load_dotenv()

api_key = os.getenv('DEEPSEEK_API_KEY', '')
if not api_key:
	raise ValueError('DEEPSEEK_API_KEY is not set')


async def run_search():
	browser = Browser(
		config=BrowserConfig(
	        # Configure the browser to connect to your Chrome instance
			# Specify the path to your Chrome executable
			browser_binary_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS path
			# For Windows, typically: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
			# For Linux, typically: '/usr/bin/google-chrome'

            # 无头模式
            headless=False, 
            disable_security=True,

            keep_alive=True,
		)
	)
	agent = Agent(
		task=(
            '在aippt网站(https://www.aippt.cn/generate?type=ai), 生成一个PPT. 主题是"人工智能学习,10页左右", ppt模版风格要贴合主题.'
            '操作提示：要打开联网搜索;点“联网搜索”旁边的纸飞机状的按钮后就会开始生成大纲.'
            '生成后，选pdf格式下载'
		),
		llm=ChatDeepSeek(
			base_url='https://api.deepseek.com/v1',
			model='DeepSeek-VL2',
			api_key=SecretStr(api_key),
		),
		browser=browser,

        # 视觉能力，deepseek不支持
		use_vision=True, 
	)

	await agent.run()

if __name__ == '__main__':
	asyncio.run(run_search())
