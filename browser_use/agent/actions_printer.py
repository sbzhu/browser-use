import json
import logging
from pathlib import Path
from typing import Any

from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig

logger = logging.getLogger(__name__)


class ActionsPrinter:
	def __init__(
		self,
		history_list: list[dict[str, Any]],
		sensitive_data_keys: list[str] | None = None,
		browser_config: BrowserConfig | None = None,
		context_config: BrowserContextConfig | None = None,
	):
		"""
		Initializes the script generator.

		Args:
		    history_list: A list of dictionaries, where each dictionary represents an AgentHistory item.
		                 Expected to be raw dictionaries from `AgentHistoryList.model_dump()`.
		    sensitive_data_keys: A list of keys used as placeholders for sensitive data.
		    browser_config: Configuration from the original Browser instance.
		    context_config: Configuration from the original BrowserContext instance.
		"""
		self.history = history_list
		self.sensitive_data_keys = sensitive_data_keys or []
		self.browser_config = browser_config
		self.context_config = context_config
		self._imports_helpers_added = False
		self._page_counter = 0  # Track pages for tab management

		# Dictionary mapping action types to handler methods
		self._action_handlers = {
			'go_to_url': self._map_go_to_url,
			'wait': self._map_wait,
			'input_text': self._map_input_text,
			'click_element': self._map_click_element,
			'click_element_by_index': self._map_click_element,  # Map legacy action
			'scroll_down': self._map_scroll_down,
			'scroll_up': self._map_scroll_up,
			'send_keys': self._map_send_keys,
			'go_back': self._map_go_back,
			'open_tab': self._map_open_tab,
			'close_tab': self._map_close_tab,
			'switch_tab': self._map_switch_tab,
			'search_google': self._map_search_google,
			'drag_drop': self._map_drag_drop,
			'extract_content': self._map_extract_content,
			'click_download_button': self._map_click_download_button,
			'done': self._map_done,
		}

	def _generate_browser_launch_args(self) -> str:
		"""Generates the arguments string for browser launch based on BrowserConfig."""
		if not self.browser_config:
			# Default launch if no config provided
			return 'headless=False'

		args_dict = {
			'headless': self.browser_config.headless,
			# Add other relevant launch options here based on self.browser_config
			# Example: 'proxy': self.browser_config.proxy.model_dump() if self.browser_config.proxy else None
			# Example: 'args': self.browser_config.extra_browser_args # Be careful inheriting args
		}
		if self.browser_config.proxy:
			args_dict['proxy'] = self.browser_config.proxy.model_dump()

		# Filter out None values
		args_dict = {k: v for k, v in args_dict.items() if v is not None}

		# Format as keyword arguments string
		args_str = ', '.join(f'{key}={repr(value)}' for key, value in args_dict.items())
		return args_str

	def _generate_context_options(self) -> str:
		"""Generates the options string for context creation based on BrowserContextConfig."""
		if not self.context_config:
			return ''  # Default context

		options_dict = {}

		# Map relevant BrowserContextConfig fields to Playwright context options
		if self.context_config.user_agent:
			options_dict['user_agent'] = self.context_config.user_agent
		if self.context_config.locale:
			options_dict['locale'] = self.context_config.locale
		if self.context_config.permissions:
			options_dict['permissions'] = self.context_config.permissions
		if self.context_config.geolocation:
			options_dict['geolocation'] = self.context_config.geolocation
		if self.context_config.timezone_id:
			options_dict['timezone_id'] = self.context_config.timezone_id
		if self.context_config.http_credentials:
			options_dict['http_credentials'] = self.context_config.http_credentials
		if self.context_config.is_mobile is not None:
			options_dict['is_mobile'] = self.context_config.is_mobile
		if self.context_config.has_touch is not None:
			options_dict['has_touch'] = self.context_config.has_touch
		if self.context_config.save_recording_path:
			options_dict['record_video_dir'] = self.context_config.save_recording_path
		if self.context_config.save_har_path:
			options_dict['record_har_path'] = self.context_config.save_har_path

		# Handle viewport/window size
		if self.context_config.no_viewport:
			options_dict['no_viewport'] = True
		elif hasattr(self.context_config, 'window_width') and hasattr(self.context_config, 'window_height'):
			options_dict['viewport'] = {
				'width': self.context_config.window_width,
				'height': self.context_config.window_height,
			}

		# Note: cookies_file and save_downloads_path are handled separately

		# Filter out None values
		options_dict = {k: v for k, v in options_dict.items() if v is not None}

		# Format as keyword arguments string
		options_str = ', '.join(f'{key}={repr(value)}' for key, value in options_dict.items())
		return options_str

	def _get_imports_and_helpers(self) -> list[str]:
		"""Generates necessary import statements (excluding helper functions)."""
		# Return only the standard imports needed by the main script body
		return [
			'import asyncio',
			'import json',
			'import os',
			'import sys',
			'from pathlib import Path',  # Added Path import
			'import urllib.parse',  # Needed for search_google
			'from patchright.async_api import async_playwright, Page, BrowserContext',  # Added BrowserContext
			'from dotenv import load_dotenv',
			'',
			'# Load environment variables',
			'load_dotenv(override=True)',
			'',
			# Helper function definitions are no longer here
		]

	def _get_sensitive_data_definitions(self) -> list[str]:
		"""Generates the SENSITIVE_DATA dictionary definition."""
		if not self.sensitive_data_keys:
			return ['SENSITIVE_DATA = {}', '']

		lines = ['# Sensitive data placeholders mapped to environment variables']
		lines.append('SENSITIVE_DATA = {')
		for key in self.sensitive_data_keys:
			env_var_name = key.upper()
			default_value_placeholder = f'YOUR_{env_var_name}'
			lines.append(f'    "{key}": os.getenv("{env_var_name}", {json.dumps(default_value_placeholder)}),')
		lines.append('}')
		lines.append('')
		return lines

	def _get_selector_for_action(self, history_item: dict, action_index_in_step: int) -> str | None:
		"""
		Gets the selector (preferring XPath) for a given action index within a history step.
		Formats the XPath correctly for Playwright.
		"""
		state = history_item.get('state')
		if not isinstance(state, dict):
			return None
		interacted_elements = state.get('interacted_element')
		if not isinstance(interacted_elements, list):
			return None
		if action_index_in_step >= len(interacted_elements):
			return None
		element_data = interacted_elements[action_index_in_step]
		if not isinstance(element_data, dict):
			return None

		return element_data.get('text_content')

	def _get_goto_timeout(self) -> int:
		"""Gets the page navigation timeout in milliseconds."""
		default_timeout = 90000  # Default 90 seconds
		if self.context_config and self.context_config.maximum_wait_page_load_time:
			# Convert seconds to milliseconds
			return int(self.context_config.maximum_wait_page_load_time * 1000)
		return default_timeout

	# --- Action Mapping Methods ---
	def _map_go_to_url(self, params: dict, step_info_str: str, action_type:str, **kwargs) -> list[str]:
		url = params.get('url')
		return [
			f'{action_type} url={url}',
		]

	def _map_wait(self, params: dict, step_info_str: str, action_type:str, **kwargs) -> list[str]:
		seconds = params.get('seconds', 3)
		return [
			f'{action_type} seconds={seconds}',
		]

	def _map_input_text(
		self, params: dict, history_item: dict, action_index_in_step: int, step_info_str: str, action_type: str, **kwargs
	) -> list[str]:
		text = params.get('text', '')
		text_content = self._get_selector_for_action(history_item, action_index_in_step)
		return [
			f'{action_type} text_content={text_content}, text={text}'
		]

	def _map_click_element(
		self, params: dict, history_item: dict, action_index_in_step: int, step_info_str: str, action_type: str, **kwargs
	) -> list[str]:
		text_content = self._get_selector_for_action(history_item, action_index_in_step)
		return [
			f'{action_type} text_content={text_content}'
		]

	def _map_scroll_down(self, params: dict, step_info_str: str, action_type:str, **kwargs) -> list[str]:
		amount = params.get('amount')
		return [
			f'{action_type} amount={amount}'
		]

	def _map_scroll_up(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		amount = params.get('amount')
		return [
			f'{action_type} amount={amount}'
		]

	def _map_send_keys(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		keys = params.get('keys')
		return [
			f'{action_type} keys={keys}'
		]

	def _map_go_back(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		goto_timeout = self._get_goto_timeout()
		return [
			f'{action_type} goto_timeout={goto_timeout}'
		]

	def _map_open_tab(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		url = params.get('url')
		goto_timeout = self._get_goto_timeout()
		return [
			f'{action_type} url={url}, goto_timeout={goto_timeout}'
		]

	def _map_close_tab(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		page_id = params.get('page_id')
		return [
			f'{action_type} page_id={page_id}'
		]

	def _map_switch_tab(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		page_id = params.get('page_id')
		return [
			f'{action_type} page_id={page_id}'
		]

	def _map_search_google(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		query = params.get('query')
		goto_timeout = self._get_goto_timeout()
		return [
			f'{action_type} query={query}, goto_timeout={goto_timeout}'
		]

	def _map_drag_drop(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		return []

	def _map_extract_content(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		goal = params.get('goal', 'content')
		return [
			f'{action_type} goal={goal}'
		]

	def _map_click_download_button(
		self, params: dict, history_item: dict, action_index_in_step: int, step_info_str: str, action_type: str, **kwargs
	) -> list[str]:
		text_content = self._get_selector_for_action(history_item, action_index_in_step)
		download_dir_in_script = "'./files'"  # Default
		return [
			f'{action_type} download_dir_in_script={download_dir_in_script}, text_content={text_content}'
		]

	def _map_done(self, params: dict, step_info_str: str, action_type: str, **kwargs) -> list[str]:
		return [
			f'{action_type}'
		]

	def _map_action_to_playwright(
		self,
		action_dict: dict,
		history_item: dict,
		previous_history_item: dict | None,
		action_index_in_step: int,
		step_info_str: str,
	) -> list[str]:
		"""
		Translates a single action dictionary into Playwright script lines using dictionary dispatch.
		"""
		if not isinstance(action_dict, dict) or not action_dict:
			return [f'            # Invalid action format: {action_dict} ({step_info_str})']

		action_type = next(iter(action_dict.keys()), None)
		params = action_dict.get(action_type)

		if not action_type or params is None:
			if action_dict == {}:
				return [f'            # Empty action dictionary found ({step_info_str})']
			return [f'            # Could not determine action type or params: {action_dict} ({step_info_str})']

		# Get the handler function from the dictionary
		handler = self._action_handlers.get(action_type)

		if handler:
			# Call the specific handler method
			return handler(
				params=params,
				history_item=history_item,
				action_index_in_step=action_index_in_step,
				step_info_str=step_info_str,
				action_type=action_type,  # Pass action_type for legacy handling etc.
				previous_history_item=previous_history_item,
			)
		else:
			# Handle unsupported actions
			logger.warning(f'Unsupported action type encountered: {action_type} ({step_info_str})')
			return [f'            # Unsupported action type: {action_type} ({step_info_str})']

	def generate_script_content(self) -> str:
		"""Generates the full Playwright script content as a string."""
		script_lines = []
		self._page_counter = 0  # Reset page counter for new script generation

		if not self._imports_helpers_added:
			#script_lines.extend(self._get_imports_and_helpers())
			self._imports_helpers_added = True

		# Read helper script content
		helper_script_path = Path(__file__).parent / 'playwright_script_helpers.py'
		try:
			with open(helper_script_path, encoding='utf-8') as f_helper:
				helper_script_content = f_helper.read()
		except FileNotFoundError:
			logger.error(f'Helper script not found at {helper_script_path}. Cannot generate script.')
			return '# Error: Helper script file missing.'
		except Exception as e:
			logger.error(f'Error reading helper script {helper_script_path}: {e}')
			return f'# Error: Could not read helper script: {e}'

		#script_lines.extend(self._get_sensitive_data_definitions())

		# Add the helper script content after imports and sensitive data
		#script_lines.append('\n# --- Helper Functions (from playwright_script_helpers.py) ---')
		#script_lines.append(helper_script_content)
		#script_lines.append('# --- End Helper Functions ---')

		# Generate browser launch and context creation code
		browser_launch_args = self._generate_browser_launch_args()
		context_options = self._generate_context_options()
		# Determine browser type (defaulting to chromium)
		browser_type = 'chromium'
		if self.browser_config and self.browser_config.browser_class in ['firefox', 'webkit']:
			browser_type = self.browser_config.browser_class


		# Add cookie loading logic if cookies_file is specified
		if self.context_config and self.context_config.cookies_file:
			cookies_file_path = repr(self.context_config.cookies_file)

		action_counter = 0
		stop_processing_steps = False
		previous_item_dict = None

		for step_index, item_dict in enumerate(self.history):
			if stop_processing_steps:
				break

			if not isinstance(item_dict, dict):
				logger.warning(f'Skipping step {step_index + 1}: Item is not a dictionary ({type(item_dict)})')
				previous_item_dict = item_dict
				continue

			model_output = item_dict.get('model_output')

			if not isinstance(model_output, dict) or 'action' not in model_output:
				script_lines.append('            # No valid model_output or action found for this step')
				previous_item_dict = item_dict
				continue

			actions = model_output.get('action')
			if not isinstance(actions, list):
				script_lines.append(f'            # Actions format is not a list: {type(actions)}')
				previous_item_dict = item_dict
				continue

			for action_index_in_step, action_detail in enumerate(actions):
				action_counter += 1

				step_info_str = f'Step {step_index + 1}, Action {action_index_in_step + 1}'
				action_lines = self._map_action_to_playwright(
					action_dict=action_detail,
					history_item=item_dict,
					previous_history_item=previous_item_dict,
					action_index_in_step=action_index_in_step,
					step_info_str=step_info_str,
				)
				print(action_lines)
				script_lines.extend(action_lines)

				action_type = next(iter(action_detail.keys()), None) if isinstance(action_detail, dict) else None
				if action_type == 'done':
					stop_processing_steps = True
					break

			previous_item_dict = item_dict

		return '\n'.join(script_lines)
