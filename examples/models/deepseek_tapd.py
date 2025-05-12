import asyncio
import os
import argparse
import json

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser import browser
from browser_use.browser.context import BrowserContextConfig
from langchain_openai import ChatOpenAI

# dotenv
load_dotenv()

api_key = os.getenv('DEEPSEEK_API_KEY', '')
if not api_key:
	raise ValueError('DEEPSEEK_API_KEY is not set')


async def run_search(tapd):
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
            f'打开tapd(https://tapd.woa.com/tapd_fe/10121621/story/list?useScene=storyList&groupType=&conf_id=1010121621076668439)，搜索这个需求"{tapd}"，'
			'查一下这个需求的状态和提交需求的时间, 如果匹配到多个TAPD，就打开第一个并读取.'
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


	print(history.action_results()[-1].extracted_content)
	
	# 从历史记录中获取最后一个模型输出
	last_output = history.action_results()[-1].extracted_content
	
	if not last_output:
		return None
		
	# 尝试从输出中提取状态和时间信息
	status = None
	submit_time = None
	
	# 将输出转换为小写，便于搜索
	output_lower = last_output.lower()
	
	# 搜索状态相关的关键词
	status_keywords = ['status', '状态']
	for keyword in status_keywords:
		if keyword in output_lower:
			# 找到关键词后，提取其后的内容作为状态
			start_pos = output_lower.find(keyword)
			start_quote = last_output.find("'", start_pos)
			if start_quote != -1:
				end_quote = last_output.find("'", start_quote + 1)
				if end_quote != -1:
					status = last_output[start_quote + 1:end_quote]
					break
	
	# 搜索时间相关的关键词
	time_keywords = ['submitted on', '提交时间']
	for keyword in time_keywords:
		if keyword in output_lower:
			# 找到关键词后，提取其后的内容作为时间
			start_pos = output_lower.find(keyword)
			start_quote = last_output.find("'", start_pos)
			if start_quote != -1:
				end_quote = last_output.find("'", start_quote + 1)
				if end_quote != -1:
					submit_time = last_output[start_quote + 1:end_quote]
					break
	
	if status or submit_time:
		result = {}
		if status:
			result['status'] = status
		if submit_time:
			result['submit_time'] = submit_time
		print(result)
		return result
	
	return None

if __name__ == '__main__':
	# 创建命令行参数解析器
	parser = argparse.ArgumentParser(description='生成PPT的脚本')
	parser.add_argument('--tapd', type=str, default='临时放过不规范下单拦截', help='TAPD标题')
	
	# 解析命令行参数
	args = parser.parse_args()
	
	# 运行脚本，传入主题参数
	result = asyncio.run(run_search(args.tapd))
	print(result)