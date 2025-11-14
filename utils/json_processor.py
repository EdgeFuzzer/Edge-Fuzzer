"""
JSON Processor Module

This module provides utilities for processing JSON files, extracting
content from LLM responses, and handling batch API responses.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional


def extract_and_save_answer(input_json_file: str) -> None:
    """
    Extract and save the 'content' field from a JSON file.
    
    Args:
        input_json_file: Path to input JSON file
    """
    with open(input_json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    output_filename = input_json_file
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)

    raw_answer = data.get("content", "")

    with open(output_filename, "w", encoding="utf-8") as outfile:
        json.dump(raw_answer, outfile, indent=4)

    print(f"Extracted 'content' saved to: {output_filename}")


def clean_json_string(json_str: str) -> str:
    """
    Clean JSON string by converting JavaScript-style comments to Lua-style.
    
    Args:
        json_str: JSON string to clean
        
    Returns:
        Cleaned JSON string
    """
    json_str = re.sub(r'//.*', '--.*', json_str)
    return json_str


def extract_and_save_json(input_json_file: str, output_json_file: str) -> bool:
    """
    Extract JSON content from LLM response and save to file.
    
    This function parses LLM responses that contain JSON wrapped in code blocks
    and extracts the actual JSON content.
    
    Args:
        input_json_file: Path to input JSON file with LLM response
        output_json_file: Path to output JSON file
        
    Returns:
        True if successful, False otherwise
    """
    with open(input_json_file, 'r', encoding='utf-8') as file:
        input_data = json.load(file)

    if isinstance(input_data, list):
        for idx, data in enumerate(input_data):
            content = data.get("content", "")
            # Skip if content is already processed (not a string)
            if not isinstance(content, str):
                print(f"Content at index {idx} is already processed (not a string)")
                continue
                
            if content:
                match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
                
                if match:
                    extracted_json = match.group(1)
                    extracted_json = clean_json_string(extracted_json)
                    try:
                        parsed_json = json.loads(extracted_json)
                        input_data[idx]["content"] = parsed_json
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON in file {input_json_file}, index {idx}: {e}")
                else:
                    print(f"No valid JSON content found in the 'content' field of "
                          f"{input_json_file}, index {idx}")
    
    elif isinstance(input_data, dict):
        content = input_data.get("content", "")
        # Skip if content is already processed (not a string)
        if not isinstance(content, str):
            print(f"Content is already processed (not a string)")
        elif content:
            match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if match:
                extracted_json = match.group(1)
                try:
                    parsed_json = json.loads(extracted_json)
                    input_data["content"] = parsed_json
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in file {input_json_file}: {e}")
            else:
                print(f"No valid JSON content found in the 'content' field of {input_json_file}")

    with open(output_json_file, "w", encoding="utf-8") as outfile:
        json.dump(input_data, outfile, indent=4)

    print(f"JSON content has been saved to {output_json_file}")
    return True


def process_all_files_in_folder(folder_path: str) -> None:
    """
    Process all JSON files in a folder, extracting content.
    
    Args:
        folder_path: Path to folder containing JSON files
    """
    processed_count = 0
    skipped_count = 0
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            try:
                extract_and_save_answer(os.path.join(folder_path, filename))
                processed_count += 1
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                skipped_count += 1
    
    print(f"\nProcessing complete. Files processed: {processed_count}, "
          f"Files skipped: {skipped_count}")


def extract_code_snippets_from_batch(
    jsonl_file: str,
    output_dir: str = "extracted_snippets"
) -> None:
    """
    Extract Code_Snippets from a batch response JSONL file.
    
    This function processes OpenAI batch API responses and extracts
    fuzzing code snippets from the JSON content.
    
    Args:
        jsonl_file: Path to the JSONL file containing batch responses
        output_dir: Directory to save the extracted snippets
    """
    # Track seen snippets to avoid duplicates
    seen_snippets: Dict[str, set] = {}
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                # Parse the JSON line
                entry = json.loads(line)
                
                # Extract custom_id to use as filename
                custom_id = entry.get('custom_id', 'unknown')
                
                # Split custom_id into parts (e.g., "url-0parse_path" -> ["url", "0", "parse_path"])
                parts = re.match(r'([^-]+)-(\d+)(.+)', custom_id)
                if not parts:
                    print(f"Invalid custom_id format: {custom_id}")
                    continue
                    
                api, round_num, func_name = parts.groups()
                
                # Create nested directory structure
                api_dir = os.path.join(output_dir, api)
                os.makedirs(api_dir, exist_ok=True)
                
                # Get the message content
                message_content = (
                    entry.get('result', {})
                    .get('message', {})
                    .get('content', [{}])[0]
                    .get('text', '')
                )
                
                # Extract JSON content from the message
                json_match = re.search(r'```json\s*(.*?)\s*```', message_content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    try:
                        # Parse the JSON content
                        snippets_data = json.loads(json_content)
                        
                        # Create output file path - use function name without the round number
                        output_file = os.path.join(api_dir, f"{func_name[1:]}.lua")
                        
                        # Initialize set for this file if not seen before
                        if output_file not in seen_snippets:
                            seen_snippets[output_file] = set()
                        
                        # Extract and write code snippets
                        new_snippets = []
                        for item in snippets_data:
                            if "Code_Snippets" in item:
                                for snippet in item["Code_Snippets"]:
                                    # Only add snippet if we haven't seen it before
                                    if snippet not in seen_snippets[output_file]:
                                        new_snippets.append(snippet)
                                        seen_snippets[output_file].add(snippet)
                        
                        # Append new snippets to file
                        if new_snippets:
                            with open(output_file, 'a', encoding='utf-8') as out_f:
                                for snippet in new_snippets:
                                    out_f.write(f"{snippet}\n")
                            
                            print(f"Added {len(new_snippets)} snippets to {output_file}")
                        
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON content for {custom_id}: {e}")
                else:
                    print(f"No JSON content found for {custom_id}")
            
            except json.JSONDecodeError as e:
                print(f"Error parsing JSONL line: {e}")
            except Exception as e:
                print(f"Error processing entry: {e}")

