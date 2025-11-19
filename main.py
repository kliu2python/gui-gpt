import time
from vision import determine_next_action
from driver import Driver


def run_agent(url, task):
    driver = Driver()
    driver.navigate(url)
    current_action = "start"
    actions = []
    
    while current_action != "finish" and current_action != "error":
        time.sleep(1.5)
        screenshot = driver.capture_screenshot()
        next_actions = determine_next_action(
            task=task,
            screenshot=screenshot,
            previous_actions=actions
        )
        driver.execute_actions(actions=next_actions)
        
        current_action = next_actions[len(next_actions) - 1]["action"]
        actions.extend(next_actions)


if __name__ == "__main__":
    default_url = "http://10.160.13.192"
    default_task = """
        Your task is to follow the following series of steps:
        1. Sign into the FGT. The username is "admin". The password is 
        "fortinet".
        2. Once you are signed into the FGT, check the side bar and click 
        each one of then to expand
        3. Once expanding, click the 2rd layer buttons to check each button's dashboard in right
        4. repeat step 2-3 for every button.
        5. record any typo or incorrect English words used.
        """
    run_agent(default_url, default_task)