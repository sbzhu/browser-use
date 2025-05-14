import asyncio
import os
import argparse

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser import browser
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
				maximum_wait_page_load_time=4.0
			),

			# 保存对话	
			save_conversation_path="logs/conversation",  # Save chat logs
		)
	)
	llm=ChatOpenAI(
		base_url=os.getenv('CUSTOM_LLM_BASE_URL', ''),
		model=os.getenv('CUSTOM_LLM_MODEL_NAME', ''),
		api_key=SecretStr(os.getenv('CUSTOM_LLM_API_KEY', '')),
	)
	llm_r=ChatDeepSeek(
		base_url='https://api.deepseek.com/v1',
		model='deepseek-reasoner',
		api_key=SecretStr(api_key),
	)
	agent = Agent(
		task=(
            #f'打开aippt网站(https://www.aippt.cn/generate?type=ai), 输入主题”我试一下, 关闭浏览器“.'
            f'在AIPPT网站(https://www.aippt.cn/generate?type=ai), 生成一个PPT. 主题是"{theme}", ppt模版风格要贴合主题.'
            '操作提示：点击"联网搜索"按钮右边一个纸飞机状的按钮后就会开始生成大纲.'
            #'AIPPT网站生成完成ppt后，点击"下载"按钮下载ppt到本地.'
		),
		message_context=(
			'根据上次执行任务的经验，完整的操作流程大致如下：\n'
			'go_to_url url=https://www.aippt.cn/generate?type=ai\n'
			'input_text text_content=, text={主题}\n'
			'click_element_by_index text_content=, description=点击后开始生成大纲\n'
			'wait seconds=40, description=等待大纲生成完成\n'
			'click_element_by_index text_content=挑选 PPT 模板\n'
			'input_text text_content=, text={主题}, description=输入模板关键词\n'
			'click_element_by_index text_content=, description=搜索合适的模板\n'
			'click_element_by_index text_content=生成 PPT1\n'
			'wait seconds=30, description=等待PPT生成\n'
			'click_element_by_index text_content=下 载\n'
			'done'
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
	history.save_to_file('history.json')
	print('history.model_actions', history.model_actions())
	#print('history.action_results', history.action_results())

	history.save_as_playwright_script('history_playwright.py')
	history.save_as_action_list("action_list.json")

	# await browser.close()

if __name__ == '__main__':
	# 创建命令行参数解析器
	parser = argparse.ArgumentParser(description='生成PPT的脚本')
	parser.add_argument('--theme', type=str, default='长生秘诀', help='PPT的主题')
	
	# 解析命令行参数
	args = parser.parse_args()
	
	# 运行脚本，传入主题参数
	asyncio.run(run_search(args.theme))
