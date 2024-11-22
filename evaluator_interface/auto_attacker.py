
import sys
import json
from typing import Optional


SPLIT_STR = ":"
IGNORE_CHARS = [".", "_"]


class SystemInteraction:
    
    def __init__(self, target, payload):
        self.target = target
        self.payload = payload
        
    def __str__(self) -> str:
        return f"{__class__.__name__}({self.payload} -> {self.target})"


class EvaluatorAction:

    def __init__(self, name, interactions) -> None:
        self.name = name
        self.interactions = interactions

    def __str__(self) -> str:
        result = f"{__class__.__name__} '{self.name}'"
        for interaction in self.interactions:
            result += f"\n\t{interaction}"
        return result
    
    def __repr__(self) -> str:
        return self.__str__()


class TestScenario:

    def __init__(self, actions, targets) -> None:
        self.actions = actions
        self.targets = targets
        self.fds = {}
        
        for target in self.targets:
            self.open_target(target)
            
    def open_target(self, target):
        try:
            self.fds[target] = open(target, "wb")
        except Exception as e:
            print(f"Could not open file descriptor for {target}: {e}")
            return False
        return True

    def __str__(self) -> str:
        result = f"{__class__.__name__}"
        for action in self.actions:
            result += f"\n{action}"
        return result
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def run(self):
        for action in self.actions:
            print(f"Running action '{action.name}'")
            for interaction in action.interactions:
                target = interaction.target
                payload = interaction.payload
                fd = self.fds[target]
                fd.write(payload)
                fd.flush()
                print(f"Sent '{payload}' to {target}")
        print("Done!")


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
    
    actions = []
    targets = json_scenario["targets"]

    for json_action in json_scenario["actions"]:
        action_name = json_action["name"]
        
        interactions = []
        for json_interaction in json_action["interactions"]:
            target_index = json_interaction["target_index"]
            target = targets[target_index]
            
            payload = json_interaction["payload"]
            for char in IGNORE_CHARS:
                payload = payload.replace(char, "")    
            payload = bytes.fromhex(payload)
            
            interaction = SystemInteraction(target, payload)
            interactions.append(interaction)
        
        action = EvaluatorAction(action_name, interactions)
        actions.append(action)
    
    scenario = TestScenario(actions, targets)
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

    scenario.run()


if __name__ == "__main__":
    main()