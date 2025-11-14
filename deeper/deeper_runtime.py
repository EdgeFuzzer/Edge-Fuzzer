"""
Deeper Runtime Module

This module provides advanced multi-round fuzzing capabilities, including
log analysis, iterative case generation, and batch processing.
"""

import os
import json
import subprocess
import time
from typing import List, Dict, Any, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from config.api_config import FUZZING_API_CHOICES, FUNC_SUM
from config.constants import ENV_OPENAI_API_KEY
from utils.case_extractor import extract_log_content
from deeper.batch_processor import (
    get_openai_client,
    create_batch_from_jsonl,
    check_batch_results
)


def generate_jsonl_for_conversion(
    input_base_folder: str = "deeper",
    output_jsonl_file: str = "batch_prompts.jsonl"
) -> str:
    """
    Generate JSONL file for converting test cases to Lua format.
    
    This function reads text files containing test cases and creates
    batch API requests to convert them to proper Lua code with pcall().
    
    Args:
        input_base_folder: Base folder containing test case text files
        output_jsonl_file: Output JSONL file path
        
    Returns:
        Path to generated JSONL file
    """
    with open(output_jsonl_file, "w", encoding="utf-8") as jsonl_file:
        request_count = 0
        
        for api_name in FUZZING_API_CHOICES:
            api_dir = os.path.join(input_base_folder, api_name)
            if not os.path.isdir(api_dir):
                continue

            for filename in os.listdir(api_dir):
                if filename.endswith(".txt"):
                    txt_filepath = os.path.join(api_dir, filename)

                    with open(txt_filepath, "r", encoding="utf-8") as file:
                        code_snippets = file.read().strip()

                    if not code_snippets:
                        print(f"Skipping empty file: {txt_filepath}")
                        continue

                    formatted_prompt = f"""
                        Convert the following test cases to Lua. Each line contains a fuzzing test case, 
                        possibly with multiple code snippets separated by `;`. Revise each case ensuring:
                        1. Each case runs inside `pcall()` to catch errors.
                        2. If `pcall` fails, print an error message in Lua.

                        Example format:
                        ```lua
                        success, result = pcall(MgmtBindRequest.from_values, {{}}, coroutine.create(function() end))
                        if not success then print("Test Case: Coroutine as start_index - Error:", result) end```
                        Now, convert the following: {code_snippets} 
                    """

                    custom_id = f"request-{request_count}__{api_name}__{filename.replace('.txt', '.lua')}"
                    json_entry = {
                        "custom_id": custom_id,
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": "You are a Lua expert."},
                                {"role": "user", "content": formatted_prompt}
                            ],
                            "temperature": 0.1
                        }
                    }

                    jsonl_file.write(json.dumps(json_entry) + "\n")
                    request_count += 1
                    print(f"Added batch request: {json_entry['custom_id']}")
    
    return output_jsonl_file


def deeper_generate_jsonl(
    api_source_folder: str = "./api_sources",
    fuzzing_folder: str = "deeper/round1",
    log_folder: str = "logs/deeper/round1",
    output_jsonl_file: str = "deeper_batch_prompts_rd2.jsonl"
) -> str:
    """
    Generate JSONL file for deeper round fuzzing case generation.
    
    This function creates batch requests for generating new fuzzing cases
    based on previous round results and log analysis.
    
    Args:
        api_source_folder: Folder containing API documentation and code
        fuzzing_folder: Folder containing previous round fuzzing cases
        log_folder: Folder containing edge driver logs
        output_jsonl_file: Output JSONL file path
        
    Returns:
        Path to generated JSONL file
    """
    api_code_folder = os.path.join(api_source_folder, "api_codes")
    api_doc_folder = os.path.join(api_source_folder, "api_docs")
    request_count = 0
    
    with open(output_jsonl_file, "w", encoding="utf-8") as jsonl_file:
        for api in FUZZING_API_CHOICES:
            api_code_file = os.path.join(api_code_folder, api + ".lua")
            temp = api.replace("/", "-")
            api_doc_file = os.path.join(api_doc_folder, temp + ".md")
            
            if not (os.path.exists(api_doc_file) and os.path.exists(api_code_file)):
                print(f"Error: {api_doc_file} or {api_code_file} doesn't exist")
                continue
            
            with open(api_doc_file, encoding='utf-8') as f1:
                api_doc = f1.read()
            with open(api_code_file, encoding='utf-8') as f2:
                api_code = f2.read()
            
            for func in FUNC_SUM.get(api, []):
                fuzzing_cases_file = os.path.join(fuzzing_folder, api, func + ".lua")
                edge_driver_log_file = os.path.join(log_folder, api, func + ".log")
                
                if not (os.path.exists(fuzzing_cases_file) and os.path.exists(edge_driver_log_file)):
                    print(f"Error: files {fuzzing_cases_file} or {edge_driver_log_file} doesn't exist")
                    continue

                with open(fuzzing_cases_file, encoding='utf-8') as f3:
                    random_fuzzing_case = f3.read()
                with open(edge_driver_log_file, encoding='utf-8') as f4:
                    edge_driver_log = f4.read()

                # First prompt: Analyze logs
                formatted_prompt = f"""
                    You are a security expert analyzing logs from a smartthings edge driver. 
                    ## Context 
                    Code snippets given to fuzz:
                    {random_fuzzing_case}
                    Log of Edge Driver:
                    {edge_driver_log}
                    API code:
                    {api_code}
                    API doc:
                    {api_doc}
                    Based on the above logs, please analyze if any potential vulnerabilities were found 
                    in the application or driver. Specifically, look for any abnormal behaviors, crash 
                    reports, memory leaks, or security issues. After that, please conclude the potential 
                    fuzzing directions based on the logs, starting with "Fuzzing Directions:". Please note 
                    that all testing code snippets in the Edge Driver Log are called with the function pcall().
                """
                
                # Second prompt: Generate new cases
                second_prompt = f"""
                    As the Fuzzing Directions you provided, please mutate at least 10 fuzzing cases.
                    Based on the edge driver log, please avoid to mutate the fuzzing cases that couldn't 
                    pass the data validation. In other words, make sure to consider any validation 
                    requirements mentioned in the API documentation while mutating the fuzzing cases that 
                    could pass the validation while exploring the potential vulnerabilities.
                    You may start from the fuzzing cases that run successfully in the edge driver log. 
                    (Note that the order of the fuzzing cases in the log is the same as the order of the 
                    fuzzing cases in the code snippets.)
                    Please generate the lua code with pcall() for each case. You may only include the 
                    code snippets that would be run. 
                    Note that a valid IEEE address is in format of "\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00".
                """
                
                custom_id = f"request-{request_count}__{api}__{func}.lua"
                json_entry = {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": "You are a Lua expert."},
                            {"role": "user", "content": formatted_prompt},
                            {"role": "user", "content": second_prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 16000
                    }
                }

                jsonl_file.write(json.dumps(json_entry) + "\n")
                request_count += 1
                print(f"Added batch request: {json_entry['custom_id']}")
    
    return output_jsonl_file


def run_command(
    command: str,
    input_sequence: Optional[List[tuple]] = None,
    delay_after: int = 5
) -> None:
    """
    Run a shell command with optional input sequence.
    
    Args:
        command: Command to run
        input_sequence: List of (input_text, delay) tuples
        delay_after: Delay after command completes
    """
    process = subprocess.Popen(command, stdin=subprocess.PIPE, text=True, shell=True)

    if input_sequence:
        for input_text, delay in input_sequence:
            time.sleep(delay)
            process.stdin.write(input_text + "\n")
            process.stdin.flush()

    time.sleep(delay_after)
    process.stdin.close()
    process.wait()


def deeper_round(
    api_source_folder: str = "./api_sources",
    fuzzing_folder: str = "deeper/round1",
    log_folder: str = "logs/deeper/round1",
    output_folder: str = "deeper/round4",
    output_jsonl: str = "deeper_batch_prompts_rd3.jsonl",
    job_name: str = "deeper_round3"
) -> Optional[str]:
    """
    Execute a deeper fuzzing round.
    
    This function orchestrates a complete deeper round:
    1. Extract relevant log content
    2. Generate batch requests
    3. Create and monitor batch job
    4. Process results
    
    Args:
        api_source_folder: Folder containing API sources
        fuzzing_folder: Folder with previous round cases
        log_folder: Folder with edge driver logs
        output_folder: Folder for output files
        output_jsonl: JSONL file for batch requests
        job_name: Job identifier
        
    Returns:
        Batch ID if successful, None otherwise
    """
    # Extract log content
    extract_log_content(directory=log_folder)
    
    # Generate batch requests
    deeper_generate_jsonl(
        api_source_folder=api_source_folder,
        fuzzing_folder=fuzzing_folder,
        log_folder=log_folder,
        output_jsonl_file=output_jsonl
    )
    
    # Create batch job
    batch_id = create_batch_from_jsonl(output_jsonl, job=job_name)
    if not batch_id:
        return None
    
    # Check and process results
    check_batch_results(batch_id, out_folder=output_folder)
    
    return batch_id

