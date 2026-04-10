
import sys
import os
import time
import json
import subprocess
import tempfile
import base64
import codecs
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


class EvaluatorTestCase:

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

    def __init__(self, test_cases, targets) -> None:
        self.test_cases = test_cases
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
        for test_case in self.test_cases:
            result += f"\n{test_case}"
        return result
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def run(self):
        for test_case in self.test_cases:
            print(f"Running test_case '{test_case.name}'")
            for interaction in test_case.interactions:
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
    
    test_cases = []
    targets = json_scenario["targets"]

    # JSON must provide a top-level 'test_cases' array
    json_test_cases = json_scenario.get("test_cases")
    if not isinstance(json_test_cases, list):
        print(f"Error: scenario must contain a 'test_cases' array")
        return None

    for json_test_case in json_test_cases:
        test_case_name = json_test_case.get("name")
        if not test_case_name:
            print("Warning: test_case without name, skipping")
            continue

        interactions = []
        for json_interaction in json_test_case.get("interactions", []):
            target_index = json_interaction["target_index"]
            target = targets[target_index]

            payload = json_interaction["payload"]
            # Accept multiple payload formats:
            # - continuous hex string like "6368656c6c6f0a"
            # - dotted/underscored hex like "63.68.65_6c.6c.6f.0a"
            # - human-readable text with C-style escapes (e.g. "Hello\n" or "Bin\x00Data")
            def payload_to_bytes(p: str) -> bytes:
                if not isinstance(p, str):
                    raise ValueError("payload must be a string")
                # detect hex-like (allow dots/underscores as separators)
                stripped = p.replace('.', '').replace('_', '')
                is_hex = all(c in '0123456789abcdefABCDEF' for c in stripped) and (len(stripped) % 2 == 0) and len(stripped) > 0
                if is_hex:
                    return bytes.fromhex(stripped)
                # otherwise interpret C-style escapes (\n, \xNN, \uNNNN, etc.)
                decoded = codecs.decode(p, 'unicode_escape')
                # encode to latin-1 so byte values 0..255 map directly
                return decoded.encode('latin-1')

            payload_bytes = payload_to_bytes(payload)

            interaction = SystemInteraction(target, payload_bytes)
            interactions.append(interaction)

    test_case = EvaluatorTestCase(test_case_name, interactions)
    test_cases.append(test_case)

    scenario = TestScenario(test_cases, targets)
    return scenario


def hex_payload_to_bytes(payload: str) -> bytes:
    """
    Convert hex payload (format: "63.68.6f.6f...") to bytes.
    """
    # Remove dots and underscores (IGNORE_CHARS)
    hex_chars = payload.replace(".", "").replace("_", "")
    # Convert to bytes
    return bytes.fromhex(hex_chars)


def interpret_payload_to_bytes(p: str) -> bytes:
    """Interpret a payload given in several possible formats:
    - continuous hex string like "6368656c6c6f0a"
    - dotted/underscored hex like "63.68.65_6c.6c.6f.0a"
    - human-readable text with C-style escapes (e.g. "Hello\n" or "Bin\x00Data")
    Returns the raw bytes to send to the target FIFO.
    """
    if not isinstance(p, str):
        raise ValueError("payload must be a string")
    stripped = p.replace('.', '').replace('_', '')
    is_hex = all(c in '0123456789abcdefABCDEF' for c in stripped) and (len(stripped) % 2 == 0) and len(stripped) > 0
    if is_hex:
        return bytes.fromhex(stripped)
    decoded = codecs.decode(p, 'unicode_escape')
    return decoded.encode('latin-1')


def create_empty_script() -> str:

    # Create a temporary bash script
    temp_script = tempfile.NamedTemporaryFile(mode='w', suffix='.bash', delete=False)
    temp_script.close()

    os.chmod(temp_script.name, 0o755)

    return temp_script.name


def create_test_case_script(test_case_name: str, test_case_data: dict, targets: list, evaluator_actions_file: str) -> str:
    """
    Create a temporary bash script that directly executes the test_case by writing to FIFOs.
    Returns the path to the temporary script.
    """
    # Get base directory to resolve relative paths
    dirname = os.path.dirname(os.path.dirname(__file__))

    # Create a temporary bash script
    temp_script = tempfile.NamedTemporaryFile(mode='w', suffix='.bash', delete=False)
    temp_script.write("#!/bin/bash\n")
    temp_script.write(f"# Temporary script for test_case: {test_case_name}\n")
    temp_script.write(f"# Base directory: {dirname}\n\n")

    # Process each interaction in the test_case
    interactions = test_case_data.get("interactions", [])

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

        # Convert payload (hex or escaped text) to bytes, then encode as base64 for safe transmission in bash
        payload_bytes = interpret_payload_to_bytes(payload)
        base64_payload = base64.b64encode(payload_bytes).decode('ascii')

        # Write to FIFO using echo with base64 decode (safer than dealing with escape sequences)
        temp_script.write(f"# Writing to {target_path}\n")
        temp_script.write(f"echo '{base64_payload}' | base64 -d > '{fifo_path}'\n")
        temp_script.write("sleep 0.1\n")  # Small delay between interactions

    temp_script.close()

    # Make the script executable
    os.chmod(temp_script.name, 0o755)

    return temp_script.name


def run_test_cases_with_run_bash(evaluator_actions_file: str):
    """
    Read evaluator_actions.json, create temporary scripts for each test_case,
    and call run.bash for each test_case.
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
    
    # Require top-level 'test_cases' array
    test_cases = json_actions.get("test_cases")
    targets = json_actions.get("targets", [])

    if not isinstance(test_cases, list):
        print(f"No test_cases found in {evaluator_actions_file} (expecting 'test_cases' array)")
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

    monitor_version = json_actions.get("monitor_version", "bpftrace024")
    
    print(f"Found {len(test_cases)} test_cases in {evaluator_actions_file}")
    print(f"System executable: {system_executable}")
    print(f"Monitor version: {monitor_version}")
    if system_executable_args:
        print(f"System executable args: {system_executable_args}")
    # Determine system name for output reports. If not provided explicitly, derive from executable name
    system_name = json_actions.get("system_name")
    if not system_name:
        # fallback: use basename of system_executable without extension
        system_name = os.path.splitext(os.path.basename(system_executable))[0]

    # Ensure the present_result output directory exists: present_result/output/{system_name}
    report_dir = os.path.join(system_name)
    try:
        os.makedirs(report_dir, exist_ok=True)
    except Exception as e:
        print(f"Warning: could not create report dir {report_dir}: {e}")
    
    temp_scripts = []  # Keep track of temp script files for cleanup


    try:
        if len(test_cases) == 0:
            print("No test cases have been found. Running the system for 10 seconds.")
            
            test_case_name = "automatic_10_seconds_run"
            temp_script_path = create_empty_script()
            temp_scripts.append(temp_script_path)

            # Assemble a report filename under present_result/output/{system_name}
            report_path = os.path.join(report_dir, test_case_name)
            
            # Call run.bash with: 1 {report_path} 3 {temp_script} {system_executable}
            # Format: run.bash [n_exec] [report_filename] [wait_time] [evaluator_actions_script] [system_executable] [system_executable_args...]
            cmd = ["bash", run_bash_path, "1", report_path, "10", temp_script_path, ",".join(system_processes), monitor_version, system_executable]
            cmd.extend(system_executable_args)
            print(f"Executing: {' '.join(cmd)}")
            
            subprocess.run(cmd)
            print("10 seconds run finished")

        else :
            for test_case in test_cases:
                test_case_name = test_case.get("name")
                if not test_case_name:
                    print("Warning: Test case without name, skipping")
                    continue

                print(f"\n{'='*60}")
                print(f"Processing test_case: {test_case_name}")
                print(f"{'='*60}")

                # Create temporary script for this test_case
                temp_script_path = create_test_case_script(test_case_name, test_case, targets, evaluator_actions_file)
                temp_scripts.append(temp_script_path)

                # Assemble a report filename under present_result/output/{system_name}
                report_path = os.path.join(report_dir, test_case_name)
                
                # Call run.bash with: 1 {report_path} 3 {temp_script} {system_executable}
                # Format: run.bash [n_exec] [report_filename] [wait_time] [evaluator_actions_script] [system_executable] [system_executable_args...]
                cmd = ["bash", run_bash_path, "1", report_path, "3", temp_script_path, ",".join(system_processes), monitor_version, system_executable]
                cmd.extend(system_executable_args)
                print(f"Executing: {' '.join(cmd)}")
                
                try:
                    subprocess.run(cmd, check=True)
                    print(f"Test case '{test_case_name}' completed successfully")
                except subprocess.CalledProcessError as e:
                    print(f"Error: Test case '{test_case_name}' failed with exit code {e.returncode}")
                    sys.exit(1)
                except Exception as e:
                    print(f"Error: Failed to execute run.bash for test_case '{test_case_name}': {e}")
                    sys.exit(1)
            
            print(f"\n{'='*60}")
            print("All test_cases completed successfully!")
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

    argc = len(sys.argv)
    argv = sys.argv

    if argc < 2:
        print(f"Usage: {argv[0]} <scenario>")
        sys.exit(1)

    scenario_file_path = argv[1]
    
    
    run_test_cases_with_run_bash(scenario_file_path)

if __name__ == "__main__":
    main()
