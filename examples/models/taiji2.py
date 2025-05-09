"""
Simple try of the agent.

@dev You need to add NOVITA_API_KEY to your environment variables.
"""

import asyncio
import os

from langchain_deepseek import ChatDeepSeek
from urllib3 import response

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from pydantic import SecretStr

from browser_use import Agent

# dotenv
load_dotenv()

api_key = os.getenv('CUSTOM_LLM_API_KEY', '')
if not api_key:
	raise ValueError('CUSTOM_LLM_API_KEY is not set')


async def run_search():
	llm=ChatOpenAI(
		base_url=os.getenv('CUSTOM_LLM_BASE_URL', ''),
		model=os.getenv('CUSTOM_LLM_MODEL_NAME', ''),
		api_key=SecretStr(api_key),
	)

	'''
	messages = [
		{"role": "system", "content": "You are a helpful assistant."},
		{"role": "user", "content": "Hello!"},
	]
	response = llm.invoke(messages)
	print(response)
	'''
	messages = [
		{
			'content': 'You are an AI agent designed to automate browser tasks. Your goal is to accomplish the ultimate task following the rules.\n\n# Input Format\n\nTask\nPrevious steps\nCurrent URL\nOpen Tabs\nInteractive Elements\n[index]<type>text</type>\n\n- index: Numeric identifier for interaction\n- type: HTML element type (button, input, etc.)\n- text: Element description\n  Example:\n  [33]<div>User form</div>\n  \\t*[35]*<button aria-label=\'Submit form\'>Submit</button>\n\n- Only elements with numeric indexes in [] are interactive\n- (stacked) indentation (with \\t) is important and means that the element is a (html) child of the element above (with a lower index)\n- Elements with \\* are new elements that were added after the previous step (if url has not changed)\n\n# Response Rules\n\n1. RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format:\n   {"current_state": {"evaluation_previous_goal": "Success|Failed|Unknown - Analyze the current elements and the image to check if the previous goals/actions are successful like intended by the task. Mention if something unexpected happened. Shortly state why/why not",\n   "memory": "Description of what has been done and what you need to remember. Be very specific. Count here ALWAYS how many times you have done something and how many remain. E.g. 0 out of 10 websites analyzed. Continue with abc and xyz",\n   "next_goal": "What needs to be done with the next immediate action"},\n   "action":[{"one_action_name": {// action-specific parameter}}, // ... more actions in sequence]}\n\n2. ACTIONS: You can specify multiple actions in the list to be executed in sequence. But always specify only one action name per item. Use maximum 10 actions per sequence.\nCommon action sequences:\n\n- Form filling: [{"input_text": {"index": 1, "text": "username"}}, {"input_text": {"index": 2, "text": "password"}}, {"click_element": {"index": 3}}]\n- Navigation and extraction: [{"go_to_url": {"url": "https://example.com"}}, {"extract_content": {"goal": "extract the names"}}]\n- Actions are executed in the given order\n- If the page changes after an action, the sequence is interrupted and you get the new state.\n- Only provide the action sequence until an action which changes the page state significantly.\n- Try to be efficient, e.g. fill forms at once, or chain actions where nothing changes on the page\n- only use multiple actions if it makes sense.\n\n3. ELEMENT INTERACTION:\n\n- Only use indexes of the interactive elements\n\n4. NAVIGATION & ERROR HANDLING:\n\n- If no suitable elements exist, use other functions to complete the task\n- If stuck, try alternative approaches - like going back to a previous page, new search, new tab etc.\n- Handle popups/cookies by accepting or closing them\n- Use scroll to find elements you are looking for\n- If you want to research something, open a new tab instead of using the current tab\n- If captcha pops up, try to solve it - else try a different approach\n- If the page is not fully loaded, use wait action\n\n5. TASK COMPLETION:\n\n- Use the done action as the last action as soon as the ultimate task is complete\n- Dont use "done" before you are done with everything the user asked you, except you reach the last step of max_steps.\n- If you reach your last step, use the done action even if the task is not fully finished. Provide all the information you have gathered so far. If the ultimate task is completely finished set success to true. If not everything the user asked for is completed set success in done to false!\n- If you have to do something repeatedly for example the task says for "each", or "for all", or "x times", count always inside "memory" how many times you have done it and how many remain. Don\'t stop until you have completed like the task asked you. Only call done after the last step.\n- Don\'t hallucinate actions\n- Make sure you include everything you found out for the ultimate task in the done text parameter. Do not just say you are done, but include the requested information of the task.\n\n6. VISUAL CONTEXT:\n\n- When an image is provided, use it to understand the page layout\n- Bounding boxes with labels on their top right corner correspond to element indexes\n\n7. Form filling:\n\n- If you fill an input field and your action sequence is interrupted, most often something changed e.g. suggestions popped up under the field.\n\n8. Long tasks:\n\n- Keep track of the status and subresults in the memory.\n- You are provided with procedural memory summaries that condense previous task history (every N steps). Use these summaries to maintain context about completed actions, current progress, and next steps. The summaries appear in chronological order and contain key information about navigation history, findings, errors encountered, and current state. Refer to these summaries to avoid repeating actions and to ensure consistent progress toward the task goal.\n\n9. Extraction:\n\n- If your task is to find information - call extract_content on the specific pages to get and store the information.\n  Your responses must be always JSON with the specified format.\n',
			'role': 'system'
		}, {
			'content': 'Your ultimate task is: """1. Go to https://www.reddit.com/r/LocalLLaMA 2. Search for \'browser use\' in the search bar3. Click on first result4. Return the first comment""". If you achieved your ultimate task, stop everything and use the done action in the next step to complete the task. If not, continue as usual.',
			'role': 'user'
		}, {
			'content': 'Example output:',
			'role': 'user'
		}, {
			'content': None,
			'role': 'assistant',
			'tool_calls': [{
				'type': 'function',
				'id': '1',
				'function': {
					'name': 'AgentOutput',
					'arguments': '{"current_state": {"evaluation_previous_goal": "Success - I successfully clicked on the \'Apple\' link from the Google Search results page, \\n\\t\\t\\t\\t\\t\\t\\twhich directed me to the \'Apple\' company homepage. This is a good start toward finding \\n\\t\\t\\t\\t\\t\\t\\tthe best place to buy a new iPhone as the Apple website often list iPhones for sale.", "memory": "I searched for \'iPhone retailers\' on Google. From the Google Search results page, \\n\\t\\t\\t\\t\\t\\t\\tI used the \'click_element_by_index\' tool to click on element at index [45] labeled \'Best Buy\' but calling \\n\\t\\t\\t\\t\\t\\t\\tthe tool did not direct me to a new page. I then used the \'click_element_by_index\' tool to click \\n\\t\\t\\t\\t\\t\\t\\ton element at index [82] labeled \'Apple\' which redirected me to the \'Apple\' company homepage. \\n\\t\\t\\t\\t\\t\\t\\tCurrently at step 3/15.", "next_goal": "Looking at reported structure of the current page, I can see the item \'[127]<h3 iPhone/>\' \\n\\t\\t\\t\\t\\t\\t\\tin the content. I think this button will lead to more information and potentially prices \\n\\t\\t\\t\\t\\t\\t\\tfor iPhones. I\'ll click on the link at index [127] using the \'click_element_by_index\' \\n\\t\\t\\t\\t\\t\\t\\ttool and hope to see prices on the next page."}, "action": [{"click_element_by_index": {"index": 127}}]}'
				}
			}]
		}, {
			'content': 'Browser started',
			'role': 'tool',
			'tool_call_id': '1'
		}, {
			'content': '[Your task history memory starts here]',
			'role': 'user'
		}, {
			'content': "\n[Task history memory ends]\n[Current state starts here]\nThe following is one-time information - if you need to remember it write it to memory:\nCurrent url: about:blank\nAvailable tabs:\n[TabInfo(page_id=0, url='about:blank', title='', parent_page_id=None)]\nInteractive elements from top layer of the current page inside the viewport:\nempty page\nCurrent step: 1/100Current date and time: 2025-05-08 15:56\n",
			'role': 'user'
		}
	]
	response = llm.invoke(messages)
	print(response)

	'''
	agent = Agent(
		task=(
			'1. Go to https://www.reddit.com/r/LocalLLaMA '
			"2. Search for 'browser use' in the search bar"
			'3. Click on first result'
			'4. Return the first comment'
		),
		llm=llm,
		use_vision=False,
	)

	await agent.run()
	'''


if __name__ == '__main__':
	asyncio.run(run_search())
