
import sys
import json
from typing import Optional


SPLIT_STR = ":"


class EvaluatorAction:

    def __init__(self, name, payloads) -> None:
        self.name = name
        self.payloads = payloads

    def add_payload(self, payload):
        self.payloads.append(payload)

    def __str__(self) -> str:
        return f"{__class__.__name__}({self.name} -> {self.payloads})"
    
    def __repr__(self) -> str:
        return self.__str__()


class TestScenario:

    def __init__(self, action) -> None:
        self.actions = action

    def add_action(self, action):
        self.actions.append(action)

    def __str__(self) -> str:
        return f"{__class__.__name__}({self.actions})"
    
    def __repr__(self) -> str:
        return self.__str__()


def get_file_content(scenario_file_path) -> Optional[dict]:
    scenario = None
    with open(scenario_file_path, 'r') as file:
        scenario = json.load(file)
    return scenario


def parse_scenario(scenario_file_path : str) -> Optional[TestScenario]:
    
    json_scenario = get_file_content(scenario_file_path)
    if not json_scenario:
        print(f"Could not read file {scenario_file_path}")
        return None
    
    scenario = TestScenario([])

    for action in json_scenario["actions"]:
        action_name = action["name"]
        payloads = action["payloads"]
        
        scenario.add_action(EvaluatorAction(action_name, payloads))

    return scenario
        

def main():
    argc = len(sys.argv)
    argv = sys.argv

    if argc < 2:
        print(f"Usage: {argv[0]} <scenario>")
        sys.exit(1)

    scenario_file_path = argv[1]
    
    scenario = parse_scenario(scenario_file_path)
    if not scenario:
        sys.exit(1)

    print(scenario)
    


if __name__ == "__main__":
    main()