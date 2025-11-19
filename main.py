import time
from vision import determine_next_action
from driver import Driver


def run_agent(url, task):
    driver = Driver()
    driver.navigate(url)
    current_action = "start"
    actions = []
    state = {
        "visited_menu_items": [],
        "current_menu_item": None,
        "checked_submenus": []
    }
    loop_detection = {
        "recent_actions": [],
        "max_repeat": 3
    }

    while current_action != "finish" and current_action != "error":
        time.sleep(1.5)
        screenshot = driver.capture_screenshot()

        # Create state summary for the model
        state_summary = f"""
        Progress tracking:
        - Menu items you have already fully explored: {state['visited_menu_items']}
        - Submenus you have checked in current menu: {state['checked_submenus']}
        - Current menu item you are working on: {state['current_menu_item']}

        IMPORTANT: Do not click on menu items that are already in the 'visited_menu_items' list.
        Move to the next unvisited menu item instead.
        """

        next_actions = determine_next_action(
            task=task,
            screenshot=screenshot,
            previous_actions=actions[-10:] if len(actions) > 10 else actions,  # Only send last 10 actions
            state_summary=state_summary
        )
        driver.execute_actions(actions=next_actions)

        current_action = next_actions[len(next_actions) - 1]["action"]

        # Loop detection: check if we're repeating the same action
        action_signature = f"{current_action}:{next_actions[-1].get('text', '')}"
        loop_detection["recent_actions"].append(action_signature)
        if len(loop_detection["recent_actions"]) > 5:
            loop_detection["recent_actions"].pop(0)

        # If same action repeated too many times, flag as error
        if loop_detection["recent_actions"].count(action_signature) >= loop_detection["max_repeat"]:
            print(f"WARNING: Detected loop - action '{action_signature}' repeated {loop_detection['max_repeat']} times")
            print("Consider the agent may be stuck. Recent actions:", loop_detection["recent_actions"])

        actions.extend(next_actions)


if __name__ == "__main__":
    default_url = "http://10.160.13.192"
    default_task = """
        Your task is to systematically explore the FortiGate (FGT) interface:

        1. SIGN IN:
           - Username: "admin"
           - Password: "fortinet"

        2. SYSTEMATIC MENU EXPLORATION:
           After logging in, you will see a sidebar with multiple menu items.
           For EACH menu item in the sidebar (from top to bottom):

           a) Click the menu item to expand it (if not already expanded)
           b) If it has sub-menu items (2nd level), click EACH sub-menu item one by one
           c) After clicking a sub-menu item, wait for the dashboard/page to load on the right
           d) Once you've checked all sub-menu items for that menu, move to the NEXT menu item
           e) DO NOT click the same menu item twice - track which ones you've already explored

        3. COMPLETION:
           - When you have expanded and checked ALL menu items and their sub-menus, return "finish"
           - If you encounter an error you cannot recover from, return "error"

        4. NOTES TO RECORD:
           - Pay attention to any typos or incorrect English words in the interface
           - Include these in your explanations when you see them

        IMPORTANT RULES:
        - Work through menu items in ORDER (top to bottom)
        - Do NOT revisit menu items you have already fully explored
        - For each menu item, explore ALL its sub-items before moving to the next menu
        - Use the progress tracking information provided to avoid repeating work
        """
    run_agent(default_url, default_task)
