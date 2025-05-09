import asyncio
import os
import argparse

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig

# dotenv
load_dotenv()

api_key = os.getenv('DEEPSEEK_API_KEY', '')
if not api_key:
	raise ValueError('DEEPSEEK_API_KEY is not set')


async def run_search(theme):
	browser = Browser(
		config=BrowserConfig(
	        # Configure the browser to connect to your Chrome instance
			# Specify the path to your Chrome executable
			browser_binary_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS path
			# For Windows, typically: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
			# For Linux, typically: '/usr/bin/google-chrome'

			extra_browser_args=['--remote-debugging-port=9223'],

            # 无头模式
            headless=False, 
            disable_security=True,

            # 不关闭浏览器
            keep_alive=True,

			# 指定下载路径
			new_context_config=BrowserContextConfig(save_downloads_path=os.path.join(os.path.expanduser('~'), 'Downloads'))
		)
	)
	agent = Agent(
		task=(
            f'在aippt网站(https://www.aippt.cn/generate?type=ai), 生成一个PPT. 主题是"{theme}", ppt模版风格要贴合主题.'
            '操作提示：要打开联网搜索;点"联网搜索"右边一个纸飞机状的按钮后就会开始生成大纲.'
            'aippt网站生成完成ppt后，会有一个"下载"按钮,  鼠标悬浮在按钮上可以选择下载类型，选"PPT"进行下载'
		),
		llm=ChatDeepSeek(
			base_url='https://api.deepseek.com/v1',
			model='deepseek-chat',
			api_key=SecretStr(api_key),
		),
		browser=browser,

        # 视觉能力，deepseek不支持
		use_vision=False, 
	)

	await agent.run()

if __name__ == '__main__':
	# 创建命令行参数解析器
	parser = argparse.ArgumentParser(description='生成PPT的脚本')
	parser.add_argument('--theme', type=str, default='长生秘诀', help='PPT的主题')
	
	# 解析命令行参数
	args = parser.parse_args()
	
	# 运行脚本，传入主题参数
	asyncio.run(run_search(args.theme))
