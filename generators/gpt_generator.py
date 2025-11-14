"""
GPT Generator Module

This module provides test case generation using OpenAI's GPT models.
It handles API communication, prompt formatting, and response parsing.
"""

import os
import json
import re
import ast
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import openai
except ImportError:
    openai = None

from generators.prompt_templates import (
    get_case_generation_prompt,
    get_second_round_prompt
)
from utils.file_utils import write_in_path
from config.constants import (
    ENV_OPENAI_API_KEY,
    DEFAULT_GPT_MODEL,
    DEFAULT_MAX_TOKENS
)


def request_gpt(message: str, gpt_model: str = DEFAULT_GPT_MODEL) -> str:
    """
    Send a request to GPT and get the response.
    
    Args:
        message: The prompt message to send
        gpt_model: The GPT model to use (default: gpt-4o-mini)
        
    Returns:
        The response content from GPT
        
    Raises:
        ImportError: If openai package is not installed
        ValueError: If API key is not set
    """
    if openai is None:
        raise ImportError("openai package is required. Install with: pip install openai")
    
    # Get API key from environment
    api_key = os.environ.get(ENV_OPENAI_API_KEY)
    if not api_key:
        raise ValueError(f"{ENV_OPENAI_API_KEY} environment variable not set")
    
    # Initialize client
    client = openai.OpenAI(api_key=api_key)
    
    messages = [{
        "role": "system",
        "content": "You are a helpful assistant skilled in Software Testing, and exploring vulnerabilities for IoT security."
    }]
    
    if message:
        messages.append({
            "role": "user",
            "content": message
        })
        
        print(f"Waiting for {gpt_model}...")
        
        chat = client.chat.completions.create(
            model=gpt_model,
            messages=messages,
            max_tokens=DEFAULT_MAX_TOKENS
        )
        
        reply = chat.choices[0].message.content
        print(reply)
        
        return reply
    
    return ""


def generate_cases(
    api_doc: str,
    api_code: str,
    dest_dir: str,
    dest_filename: str,
    chatgpt_model: str = DEFAULT_GPT_MODEL
) -> None:
    """
    Generate fuzzing test cases using GPT and save to file.
    
    Args:
        api_doc: API documentation text
        api_code: API source code in Lua
        dest_dir: Destination directory for output file
        dest_filename: Base filename (without extension) for output
        chatgpt_model: GPT model to use for generation
    """
    prompt = get_case_generation_prompt(api_doc, api_code, "")
    
    response = request_gpt(prompt, chatgpt_model)
    
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    write_in_path(json.dumps(response), dest_filename)
    print(f"Fuzzing file generated and stored at {dest_filename}.json")


def generate_cases_second_round(
    api_source: str,
    api: str,
    func: str,
    dest_filename: str,
    chatgpt_model: str,
    fuzzing_cases: list,
    fuzzing_results: str
) -> None:
    """
    Generate second round fuzzing cases based on previous results.
    
    Args:
        api_source: Path to API source files
        api: API name
        func: Function name
        dest_filename: Destination filename
        chatgpt_model: GPT model to use
        fuzzing_cases: Previous fuzzing cases
        fuzzing_results: Analysis results from previous round
    """
    print(f"Generating second round fuzzing file...")
    
    # Load API documentation and code
    api_doc_file = os.path.join(api_source, 'api_docs', api.replace('/', '-') + '.md')
    api_code_file = os.path.join(api_source, 'api_codes', api + '.lua')
    
    api_code = ''
    api_doc = ''
    
    if os.path.exists(api_doc_file) and os.path.exists(api_code_file):
        with open(api_doc_file, encoding='utf-8') as f1:
            api_doc = f1.read()
        with open(api_code_file, encoding='utf-8') as f2:
            api_code = f2.read()
    else:
        print(f"Error: {api_doc_file} or {api_code_file} doesn't exist")
        return
    
    # Format previous fuzzing cases
    fuzzing_cases_content = ''
    for i in range(len(fuzzing_cases)):
        fuzzing_cases_content += (f'Case: {i+1}. Description: {fuzzing_cases[i][3]}. '
                                 f'Code Snippets: {fuzzing_cases[i][4]}\n')
    
    # Extract fuzzing directions from results
    fuzzing_results_contents = fuzzing_results.split('### Fuzzing Directions:')[1] if '### Fuzzing Directions:' in fuzzing_results else fuzzing_results
    
    # Generate prompt
    prompt = get_second_round_prompt(
        api_doc,
        api_code,
        fuzzing_cases_content,
        fuzzing_results_contents,
        api,
        func
    )
    
    # Get response
    reply = request_gpt(prompt, chatgpt_model)
    
    # Extract JSON from response
    pattern = r'^```(?:\w+)?\s*\n(.*?)(?=^```)```'
    result = re.findall(pattern, reply, re.DOTALL | re.MULTILINE)
    
    if result:
        try:
            response = ast.literal_eval(result[0])
            dest_filename = dest_filename.split('.json')[0] + '-scdRd'
            write_in_path(json.dumps(response), dest_filename)
            print(f"Second round fuzzing file generated and stored at {dest_filename}")
        except (ValueError, SyntaxError) as e:
            print(f"Error parsing response: {e}")
    else:
        print("No JSON found in response")


def validate_logs_with_gpt(
    log_content_st: str,
    llm_model: str = DEFAULT_GPT_MODEL
) -> str:
    """
    Use GPT to analyze logs and identify potential vulnerabilities.
    
    Args:
        log_content_st: SmartThings Edge Driver log content
        llm_model: GPT model to use for analysis
        
    Returns:
        Analysis response from GPT
    """
    prompt = f'''
        You are a security expert analyzing logs from a smartthings edge driver. 
        
        Smartthings Edge Driver Log:
        {log_content_st}
        
        Based on the above logs, please analyze if any potential vulnerabilities were found 
        in the application or driver. Specifically, look for any abnormal behaviors, crash 
        reports, memory leaks, or security issues. After that, please conclude the potential 
        fuzzing directions based on the logs, starting with "Fuzzing Directions:".
        Please note that in the Edge Driver Log, all testing code snippets are called with 
        the function pcall().
        
        If no vulnerabilities are found, simply state that no vulnerabilities were identified.
    '''
    
    response = request_gpt(prompt, llm_model)
    return response

