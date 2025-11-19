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
        "max_repeat": 3,
        "blocked_actions": [],  # Actions that caused loops and should be avoided
        "max_blocked": 5  # Max number of different actions we can block before giving up
    }

    while current_action != "finish" and current_action != "error":
        time.sleep(1.5)
        screenshot = driver.capture_screenshot()

        # Create state summary for the model
        blocked_actions_str = ", ".join(loop_detection["blocked_actions"]) if loop_detection["blocked_actions"] else "None"
        state_summary = f"""
        Progress tracking:
        - Menu items you have already fully explored: {state['visited_menu_items']}
        - Submenus you have checked in current menu: {state['checked_submenus']}
        - Current menu item you are working on: {state['current_menu_item']}
        - Actions that caused loops and MUST BE AVOIDED: {blocked_actions_str}

        CRITICAL LOOP PREVENTION:
        - DO NOT click on any actions listed in 'blocked_actions' - they caused infinite loops
        - DO NOT click on menu items in 'visited_menu_items' - they are already explored
        - If you've clicked the same item 2 times in a row, STOP and choose a different action
        - Move to the next unvisited menu item instead
        """

        next_actions = determine_next_action(
            task=task,
            screenshot=screenshot,
            previous_actions=actions[-10:] if len(actions) > 10 else actions,  # Only send last 10 actions
            state_summary=state_summary
        )

        # Handle case when model fails to return valid actions
        if next_actions is None or len(next_actions) == 0:
            print("ERROR: Failed to get valid next actions from model")
            current_action = "error"
            break

        # Loop detection: check if we're about to repeat the same action BEFORE executing
        current_action = next_actions[len(next_actions) - 1]["action"]
        action_signature = f"{current_action}:{next_actions[-1].get('text', '')}"

        # Count how many times this action appears in recent history
        recent_count = loop_detection["recent_actions"].count(action_signature)

        # If same action repeated too many times, block it and retry
        if recent_count >= loop_detection["max_repeat"]:
            print(f"WARNING: Detected loop - action '{action_signature}' repeated {loop_detection['max_repeat']} times")
            print("Consider the agent may be stuck. Recent actions:", loop_detection["recent_actions"])

            # Add this action to blocked list
            if action_signature not in loop_detection["blocked_actions"]:
                loop_detection["blocked_actions"].append(action_signature)
                print(f"Added '{action_signature}' to blocked actions list")

                # Check if we've blocked too many actions - agent is fundamentally stuck
                if len(loop_detection["blocked_actions"]) >= loop_detection["max_blocked"]:
                    print(f"ERROR: Blocked {len(loop_detection['blocked_actions'])} different actions. Agent appears fundamentally stuck.")
                    print(f"Blocked actions: {loop_detection['blocked_actions']}")
                    current_action = "error"
                    break

            # Clear recent actions to give model a fresh start
            loop_detection["recent_actions"] = []

            # Give the model ONE more chance with the blocked action info
            # If it loops again on a different action, we'll catch it
            print("Skipping this action and asking model for a different action...")
            continue  # Skip to next iteration without executing this action

        # Action is safe to execute
        driver.execute_actions(actions=next_actions)

        # Track this action
        loop_detection["recent_actions"].append(action_signature)
        if len(loop_detection["recent_actions"]) > 5:
            loop_detection["recent_actions"].pop(0)

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
