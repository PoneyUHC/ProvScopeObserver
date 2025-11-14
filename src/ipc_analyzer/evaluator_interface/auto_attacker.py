
import sys
import os
import json
import subprocess
import tempfile
import base64
from time import sleep
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
            dirname = os.path.dirname(os.path.dirname(__file__))
            self.fds[target] = open(f"{dirname}/{target}", "wb")
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
                print(f"\tSent '{payload}' to {target}")
                sleep(0.5)
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


def hex_payload_to_bytes(payload: str) -> bytes:
    """
    Convert hex payload (format: "63.68.6f.6f...") to bytes.
    """
    # Remove dots and underscores (IGNORE_CHARS)
    hex_chars = payload.replace(".", "").replace("_", "")
    # Convert to bytes
    return bytes.fromhex(hex_chars)


def create_action_script(action_name: str, action_data: dict, targets: list, evaluator_actions_file: str) -> str:
    """
    Create a temporary bash script that directly executes the action by writing to FIFOs.
    Returns the path to the temporary script.
    """
    # Get base directory to resolve relative paths
    dirname = os.path.dirname(os.path.dirname(__file__))
    
    # Create a temporary bash script
    temp_script = tempfile.NamedTemporaryFile(mode='w', suffix='.bash', delete=False)
    temp_script.write("#!/bin/bash\n")
    temp_script.write(f"# Temporary script for action: {action_name}\n")
    temp_script.write(f"# Base directory: {dirname}\n\n")
    
    # Process each interaction in the action
    interactions = action_data.get("interactions", [])
    
    for interaction in interactions:
        target_index = interaction.get("target_index")
        payload = interaction.get("payload", "")
        
        if target_index is None or target_index >= len(targets):
            continue
        
        # Get the target FIFO path
        target_path = targets[target_index]
        # Resolve relative path
        if not os.path.isabs(target_path):
            fifo_path = os.path.join(dirname, target_path)
        else:
            fifo_path = target_path
        
        # Convert hex payload to bytes, then encode as base64 for safe transmission in bash
        payload_bytes = hex_payload_to_bytes(payload)
        base64_payload = base64.b64encode(payload_bytes).decode('ascii')
        
        # Write to FIFO using echo with base64 decode (safer than dealing with escape sequences)
        temp_script.write(f"# Writing to {target_path}\n")
        temp_script.write(f"echo '{base64_payload}' | base64 -d > '{fifo_path}'\n")
        temp_script.write("sleep 0.1\n")  # Small delay between interactions
    
    temp_script.close()
    
    # Make the script executable
    os.chmod(temp_script.name, 0o755)
    
    return temp_script.name


def run_actions_with_run_bash(evaluator_actions_file: str):
    """
    Read evaluator_actions.json, create temporary scripts for each action,
    and call run.bash for each action.
    """
    json_actions = get_file_content(evaluator_actions_file)
    if not json_actions:
        print(f"Could not read file {evaluator_actions_file}")
        sys.exit(1)
    
    # Get the path to run.bash
    dirname = os.path.dirname(os.path.dirname(__file__))
    run_bash_path = os.path.join(dirname, "scripts", "run.bash")
    
    if not os.path.exists(run_bash_path):
        print(f"Error: run.bash not found at {run_bash_path}")
        sys.exit(1)
    
    # Make sure it's executable
    os.chmod(run_bash_path, 0o755)
    
    actions = json_actions.get("actions", [])
    targets = json_actions.get("targets", [])
    
    if not actions:
        print(f"No actions found in {evaluator_actions_file}")
        sys.exit(1)


    system_executable = json_actions.get("system_executable")
    if system_executable is None:
        print("Error: system_executable must be specified in evaluator_actions.json")
        sys.exit(1)

    if not os.path.exists(system_executable):
        print(f"Error: System executable not found at {system_executable}")
        sys.exit(1)
        
    system_executable_args = json_actions.get("system_executable_args", [])
    if not isinstance(system_executable_args, list):
        print("Warning: system_executable_args must be a list; defaulting to empty list")
        system_executable_args = []
    
    system_processes = json_actions.get("system_processes", [])
    if not isinstance(system_processes, list):
        print("Warning: system_processes must be a list; defaulting to empty list")
        system_processes = []
    
    print(f"Found {len(actions)} actions in {evaluator_actions_file}")
    print(f"System executable: {system_executable}")
    if system_executable_args:
        print(f"System executable args: {system_executable_args}")
    
    temp_scripts = []  # Keep track of temp script files for cleanup
    
    try:
        for action in actions:
            action_name = action.get("name")
            if not action_name:
                print("Warning: Action without name, skipping")
                continue
            
            print(f"\n{'='*60}")
            print(f"Processing action: {action_name}")
            print(f"{'='*60}")
            
            # Create temporary script for this action
            temp_script_path = create_action_script(action_name, action, targets, evaluator_actions_file)
            temp_scripts.append(temp_script_path)
            
            # Call run.bash with: 1 {action_name} 3 {temp_script} {system_executable}
            # Format: run.bash [n_exec] [report_filename] [wait_time] [evaluator_actions_script] [system_executable] [system_executable_args...]
            cmd = ["bash", run_bash_path, "1", action_name, "3", temp_script_path, ",".join(system_processes), system_executable]
            cmd.extend(system_executable_args)
            print(f"Executing: {' '.join(cmd)}")
            
            try:
                subprocess.run(cmd, check=True)
                print(f"Action '{action_name}' completed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Error: Action '{action_name}' failed with exit code {e.returncode}")
                sys.exit(1)
            except Exception as e:
                print(f"Error: Failed to execute run.bash for action '{action_name}': {e}")
                sys.exit(1)
        
        print(f"\n{'='*60}")
        print("All actions completed successfully!")
        print(f"{'='*60}")
    
    finally:
        # Clean up temporary files
        for temp_script in temp_scripts:
            try:
                if os.path.exists(temp_script):
                    os.remove(temp_script)
            except Exception as e:
                print(f"Warning: Could not remove temporary script {temp_script}: {e}")


def main():

    # TODO : target array to target map for better readability

    argc = len(sys.argv)
    argv = sys.argv

    if argc < 2:
        print(f"Usage: {argv[0]} <scenario>")
        sys.exit(1)

    scenario_file_path = argv[1]
    
    
    run_actions_with_run_bash(scenario_file_path)

if __name__ == "__main__":
    main()