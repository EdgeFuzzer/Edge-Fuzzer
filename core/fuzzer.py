"""
Fuzzer Module

This module contains the main fuzzing orchestrator that manages the execution
of fuzzing test cases across multiple rounds. It coordinates test case loading,
execution, logging, and result analysis.
"""

import json
import datetime
import argparse
from typing import List, Optional
import os

from core.connection_manager import (
    start_server,
    send_message,
    build_json_request
)
from config.api_config import FUZZING_API_CHOICES, FUNC_SUM
from config.constants import (
    DEFAULT_HUB_IP,
    DEFAULT_FUZZ_IP,
    DEFAULT_FUZZ_PORT,
    DEFAULT_ROUND,
    DEFAULT_TOTAL_ROUNDS,
    DEFAULT_LLM_MODEL,
    DEFAULT_API_SOURCE_PATH,
    DEFAULT_LOGS_PATH,
    DEFAULT_LOG_FILE_ST,
    EXT_JSON
)


def render_test_cases_file(filename: str) -> List[list]:
    """
    Load and parse test cases from a JSON file.
    
    Args:
        filename: Path to the JSON file containing test cases
        
    Returns:
        List of test case lists, each containing:
        [Test_Case, API_Name, Function_Name, Description, Code_Snippets, Pre-operation_Python]
    """
    try:
        with open(filename, "r") as file:
            test_cases = json.load(file)
        
        test_cases_list = []
        for case in test_cases:
            test_case_sublist = [
                case.get("Test_Case"),
                case.get("API_Name"),
                case.get("Function_Name"),
                case.get("Description"),
                case.get("Code_Snippets", []),
                case.get("Pre-operation_Python", None)
            ]
            test_cases_list.append(test_case_sublist)
        
        return test_cases_list
    
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return []
    except json.JSONDecodeError:
        print("Error: Invalid JSON format.")
        return []


def random_fuzzing(args: argparse.Namespace) -> None:
    """
    Execute random fuzzing across multiple APIs and rounds.
    
    This function orchestrates the fuzzing process by:
    1. Starting a server to receive port number from fuzzing app
    2. Iterating through configured APIs and their functions
    3. Loading test cases for each round
    4. Executing test cases and sending them to the hub
    5. Processing results and generating next round cases
    
    Args:
        args: Argument namespace containing fuzzing configuration:
              - fuzz_ip: IP address of fuzzing app
              - fuzz_port: Port number for initial connection
              - hub_ip: IP address of SmartThings hub
              - round: Starting round number
              - total_round: Total number of rounds to execute
              - test_file: Test case file path or pattern
              - api_source: Path to API source files
              - llm_model: LLM model to use for case generation
              - log_file_name_st: Name for SmartThings log file
              - log_file_name_app: Name for app log file
    """
    # Start server to receive port number from fuzzing app
    port_number = start_server(args.fuzz_ip, int(args.fuzz_port))
    
    # Iterate through each API
    for api in FUZZING_API_CHOICES:
        print(f'Fuzzing the API "{api}" from {args.fuzz_ip}:{args.fuzz_port} '
              f'to the hub at {args.hub_ip}')
        
        # Iterate through each function in the API
        for func in FUNC_SUM.get(api, []):
            curr_round = int(args.round)
            log_folder = os.path.join(DEFAULT_LOGS_PATH, f'{api}-{func}-')
            
            print(f'Received port number {port_number} from {args.fuzz_port}')
            print(f'Starting fuzzing {api} {func}...')
            
            # Execute fuzzing rounds
            while curr_round <= int(args.total_round):
                print(f"##### Fuzzing Round: {curr_round} #####")
                
                # Determine test file path
                if EXT_JSON in args.test_file:
                    test_file = args.test_file
                else:
                    test_file = f"{args.test_file}{api}-{curr_round}{func}{EXT_JSON}"
                
                # Load test cases
                test_cases = render_test_cases_file(test_file)
                
                if not test_cases:
                    print("No test cases found. Exiting.")
                    return
                
                # Execute each test case
                for test_case in test_cases:
                    json_message = build_json_request(api, test_case)
                    formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    
                    print(f"{formatted_time} testing {json_message.Function_Name} of "
                          f"{json_message.API_Name} for \"{json_message.Description[:-1]}\", "
                          f"awaiting response...")
                    print("Code snippets:")
                    for code in json_message.Code_Snippets:
                        print(code)
                    
                    # Send test case to hub
                    send_message(
                        args.hub_ip,
                        port_number,
                        json.dumps(json_message.__dict__)
                    )
                
                curr_round += 1
            
            # Process results and generate next round cases
            # Note: log_validation and generate_cases_scd would be imported
            # from appropriate modules in a complete implementation
            print(f"Fuzzing completed for {api} {func}")


def case_fuzzing(args: argparse.Namespace) -> None:
    """
    Execute fuzzing for a specific set of test cases.
    
    This function is used when test cases have already been generated
    and you want to execute them directly without generating new ones.
    
    Args:
        args: Argument namespace containing:
              - api_name: Name of the API to fuzz
              - test_file: Path to test case JSON file
              - fuzz_ip: IP address of fuzzing app
              - fuzz_port: Port number for initial connection
              - hub_ip: IP address of SmartThings hub
              - round: Round number for logging
              - log_file_name_st: Name for SmartThings log file
    """
    fuzzing_api_name = args.api_name
    print(f'Fuzzing the API "{fuzzing_api_name}" from {args.fuzz_ip}:{args.fuzz_port} '
          f'to the hub at {args.hub_ip}')
    
    # Start server to receive port number
    port_number = start_server(args.fuzz_ip, int(args.fuzz_port))
    print(f'Received port number {port_number} from {args.fuzz_port}\n')
    
    # Load test cases
    test_file = args.test_file
    test_cases = render_test_cases_file(test_file)
    
    if not test_cases:
        print("No test cases found. Exiting.")
        return
    
    # Execute each test case
    for test_case in test_cases:
        json_message = build_json_request(args.api_name, test_case)
        formatted_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        print(f"{formatted_time} testing {json_message.Function_Name} of "
              f"{json_message.Test_Case}: {json_message.API_Name} for "
              f"\"{json_message.Description[:-1]}\", awaiting response...")
        print("Code snippets:")
        for code in json_message.Code_Snippets:
            print(code)
        
        # Send test case to hub
        send_message(
            args.hub_ip,
            port_number,
            json.dumps(json_message.__dict__)
        )
    
    print("Case fuzzing completed.")


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for the fuzzer.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(description="Run the fuzzer")
    
    parser.add_argument(
        "--api_name",
        type=str,
        default="zdo/mgmt_bind_request",
        choices=FUZZING_API_CHOICES,
        help="The API to fuzz"
    )
    parser.add_argument(
        "--case_fuzzing",
        type=bool,
        default=True,
        help="If test cases already been generated"
    )
    parser.add_argument(
        "--test_file",
        type=str,
        default="generate_cases_hf/fuzzing_cases/zdo/fuzzing_cases.json",
        help="Path to pre-generated test cases"
    )
    parser.add_argument(
        "--api_source",
        type=str,
        default=DEFAULT_API_SOURCE_PATH,
        help="Path to API source files"
    )
    parser.add_argument(
        "--round",
        type=str,
        default=DEFAULT_ROUND,
        help="The number of the round, corresponding to the cases generated custom_id"
    )
    parser.add_argument(
        "--total_round",
        type=str,
        default=DEFAULT_TOTAL_ROUNDS,
        help="The total number of rounds to run"
    )
    parser.add_argument(
        "--destination",
        type=str,
        default="./fuzzing_cases",
        help="The name of the folder to store generated contents"
    )
    parser.add_argument(
        "--log_file_name_st",
        type=str,
        default=DEFAULT_LOG_FILE_ST,
        help="The name of log file used for store stdout from st edge driver"
    )
    parser.add_argument(
        "--log_file_name_app",
        type=str,
        default="fuzz_log_app",
        help="The name of log file used for store stdout from fuzzing app (self)"
    )
    parser.add_argument(
        "--hub_ip",
        type=str,
        default=DEFAULT_HUB_IP,
        help="IP of the hub for fuzzing purpose"
    )
    parser.add_argument(
        "--fuzz_ip",
        type=str,
        default=DEFAULT_FUZZ_IP,
        help="IP of the fuzzing app"
    )
    parser.add_argument(
        "--fuzz_port",
        type=str,
        default=DEFAULT_FUZZ_PORT,
        help="Fuzzing port on fuzzing desktop"
    )
    parser.add_argument(
        "--llm_model",
        type=str,
        default=DEFAULT_LLM_MODEL,
        help="Which LLM model will be used for generating fuzzing cases"
    )
    parser.add_argument(
        "--vectorstore_path",
        type=str,
        default="./vectorstore",
        help="The path to saved FAISS vector store"
    )
    
    return parser


if __name__ == "__main__":
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Execute fuzzing based on mode
    if args.case_fuzzing:
        case_fuzzing(args)
    else:
        random_fuzzing(args)

