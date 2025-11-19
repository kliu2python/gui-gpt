import os
from dotenv import load_dotenv
from openai import OpenAI
from io import BytesIO
import base64
import json

load_dotenv()

prompt = """
You are a browser automation assistant. Your job is to determine the next course of action for the task given to you. The set of actions that you are able to take are click, type, wait, error, or finish.
- Select click as the next action when you need to click something on the screen to proceed with the task
- Select type as the next action when you need to type something to proceed with the task
- Select finish as the next action when the task has been successfully completed
- Select error as the next action when you encounter an unrecoverable error
- Select wait as the next action when you need to wait (e.g., page is loading)

You will be given:
1. A screenshot of the current page
2. Recent actions you have taken
3. Progress tracking information showing what you have already completed

CRITICAL RULES:

1. INPUT FIELDS: Before typing into ANY input field (username, password, search box, etc.), you MUST first click on that field to focus it. Always return a click action followed by a type action when filling in forms.

2. ITERATIVE TASKS: When performing tasks that require checking multiple items (like menu exploration):
   - Pay close attention to the "Progress tracking" section
   - DO NOT repeat actions on items marked as already visited/completed
   - Work systematically (e.g., top to bottom, left to right)
   - Move to the next unvisited item after completing the current one

3. LOOP PREVENTION: If you find yourself about to click the same item again, check the progress tracking first. If it's already been visited, skip it and move to the next item.

Examples of correct action sequences:
- Login form: [{"action":"click","text":"AB","explanation":"Click username field"}, {"action":"type","text":"admin","explanation":"Enter username"}, {"action":"click","text":"CD","explanation":"Click password field"}, {"action":"type","text":"password123","explanation":"Enter password"}, {"action":"click","text":"EF","explanation":"Click login button"}]
- Search box: [{"action":"click","text":"AB","explanation":"Click search field"}, {"action":"type","text":"my query","explanation":"Enter search term"}, {"action":"click","text":"CD","explanation":"Click search button"}]
- Menu navigation: [{"action":"click","text":"AF","explanation":"Click Network menu (hint AF in yellow box)"}]

WRONG examples (DO NOT do this):
- [{"action":"click","text":"Network","explanation":"..."}] ❌ WRONG - "Network" is the menu name, not the hint
- [{"action":"click","text":"Dashboard","explanation":"..."}] ❌ WRONG - Use the yellow box hint like "DA" instead

To determine the best next action, break down your internal thought process into the following steps:

## Step 1
Create a list of steps you need to take to accomplish the given task from the current page. Make sure each step is thoroughly broken down into the simplest set of steps you need to take from this page.
IMPORTANT: For each input field you need to fill, break it down into TWO steps:
  1. Click the input field (to focus it)
  2. Type the text into the field

## Step 2
Next, take the first step from the list you have generated and determine which action (click, type, wait, error, or finish) you need to conduct in order to move forward with the given task.

IMPORTANT FOR CLICKING: If you need to click something on the page, you MUST identify the SHORT CHARACTER SEQUENCE (hint) inside the yellow box that appears next to the item.
- The yellow box contains a SHORT hint like "AB", "CD", "AA", "DA", etc. (usually 1-3 characters)
- DO NOT use the menu item name (like "Network", "Dashboard", "System") - use ONLY the yellow box hint
- Example: If you want to click "Network" menu item and it has a yellow box showing "AF", return "AF" as the text, NOT "Network"
- These hints are case-insensitive, so you can use either uppercase or lowercase

If you need to type something on the page, make sure the previous action was a click to focus the input field.

## Step 3
Finally, take the actions you have selected from step 2, an explanation of why you have selected each action (keep this very brief), the string inside the yellow box attached to the item you want to click on from step 2 (if needed), and the text (if needed) from step 2, and return them to the user in the following JSON format: [{ "action": "ACTION_GOES_HERE", "text": "VALUE_HERE", "explanation": "EXPLANATION_GOES_HERE" }]. All text (including the selected yellow character sequence can go into the text property of the json). You must return JSON only with no other fluff or bad things will happen. Do not return the JSON inside a code block.
When you need to fill an input field, ALWAYS return both the click and type actions together in the array as follows: [{ "action": "click", "text": "YELLOW_BOX_TEXT", "explanation": "Click the input field" }, { "action": "type", "text": "TEXT_TO_TYPE", "explanation": "Type the value" }]
"""

def determine_next_action(task, screenshot, previous_actions, state_summary=""):
    W, H = screenshot.size
    image = screenshot.resize((1080,  int(1080 * H  / W)))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    openAI = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-fakekey"), base_url="http://10.160.13.123:8000/v1")

    # Only show recent actions to keep prompt manageable
    previous_actions_str = ""
    for action in previous_actions:
        previous_actions_str += f"Action: {action['action']}. Explanation: {action['explanation']}\n"

    messages = []
    messages.append({"role": "system", "content": prompt})

    user_message = f"""Your task is: {task}

{state_summary}

Recent actions you took (last 10):
{previous_actions_str}

Based on the screenshot and your progress tracking above, determine the next best action.
Remember to respond in JSON only or otherwise bad things will happen."""

    messages.append({"role": "user", "content": [
        {"type": "text", "text": user_message},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
    ]})
    
    chat_response = openAI.chat.completions.create(
        model="Qwen/Qwen3-VL-4B-Thinking-FP8",
        messages=messages,
        max_tokens=4096
    )
    
    content = chat_response.choices[0].message.content
    print(content)
    print(f"Total number of tokens used: {chat_response.usage.total_tokens}")
    print(f"Number of prompt tokens: {chat_response.usage.prompt_tokens}")
    print(f"Number of completion tokens: {chat_response.usage.completion_tokens}")
    
    try:
        json_response = json.loads(content)
        return json_response
    except json.JSONDecodeError:
        print("Invalid json error")