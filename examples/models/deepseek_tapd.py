import asyncio
import os
import argparse

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser import browser
from browser_use.browser.context import BrowserContextConfig

# dotenv
load_dotenv()

api_key = os.getenv('DEEPSEEK_API_KEY', '')
if not api_key:
	raise ValueError('DEEPSEEK_API_KEY is not set')


async def run_search(tapd_id):
	browser = Browser(
		config=BrowserConfig(
	        # Configure the browser to connect to your Chrome instance
			# Specify the path to your Chrome executable
			browser_binary_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS path
			# For Windows, typically: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
			# For Linux, typically: '/usr/bin/google-chrome'
			extra_browser_args=[
				"--user-data-dir=~/Library/Application Support/Google/Chrome/Default",
				"--remote-debugging-port=9222",
        	],

            # 无头模式
            headless=False, 
            disable_security=True,

            # 不关闭浏览器
            keep_alive=True,

			# 指定下载路径
			new_context_config=BrowserContextConfig(
				save_downloads_path=os.path.join(os.path.expanduser('~'), 'Downloads'),
				maximum_wait_page_load_time=2.0
			),

			# 保存对话	
			save_conversation_path="logs/conversation",  # Save chat logs
		)
	)
	llm=ChatDeepSeek(
		base_url='https://api.deepseek.com/v1',
		model='deepseek-chat',
		api_key=SecretStr(api_key),
	)
	llm_r=ChatDeepSeek(
		base_url='https://api.deepseek.com/v1',
		model='deepseek-reasoner',
		api_key=SecretStr(api_key),
	)
	agent = Agent(
		task=(
            f'打开tapd(https://tapd.woa.com/tapd_fe/10121621/story/list?useScene=storyList&groupType=&conf_id=1010121621076668439)，搜索这个需求"{tapd_id}"，'
			'查一下这个需求的状态和提交需求的时间'
		),
		llm=llm,

		# 计划器
		# planner_llm=llm_r, 
		planner_interval=3, # Plan every 3 steps

		browser=browser,

        # 视觉能力，deepseek不支持
		use_vision=False, 
	)

	history = await agent.run()

	#print('history actions', history.model_actions())
	history.save_as_playwright_script('history_playwright.py')

	# await browser.close()

if __name__ == '__main__':
	# 创建命令行参数解析器
	parser = argparse.ArgumentParser(description='生成PPT的脚本')
	parser.add_argument('--tapd_id', type=str, default='119088168', help='TAPD需求ID')
	
	# 解析命令行参数
	args = parser.parse_args()
	
	# 运行脚本，传入主题参数
	asyncio.run(run_search(args.tapd_id))
