"""
Batch Processor Module

This module provides utilities for processing OpenAI batch API responses,
extracting Lua code, and organizing output files.
"""

import os
import json
import re
from typing import Optional, Dict, Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from config.constants import ENV_OPENAI_API_KEY


def get_openai_client() -> Any:
    """
    Get an initialized OpenAI client.
    
    Returns:
        OpenAI client instance
        
    Raises:
        ImportError: If openai package is not installed
        ValueError: If API key is not set
    """
    if OpenAI is None:
        raise ImportError("openai package required. Install with: pip install openai")
    
    api_key = os.environ.get(ENV_OPENAI_API_KEY)
    if not api_key:
        raise ValueError(f"{ENV_OPENAI_API_KEY} environment variable not set")
    
    return OpenAI(api_key=api_key)


def extract_lua_code(response_text: str) -> str:
    """
    Extract Lua code blocks from response text.
    
    Args:
        response_text: Response text containing Lua code blocks
        
    Returns:
        Extracted Lua code as string
    """
    lua_blocks = re.findall(r"```lua(.*?)```", response_text, re.DOTALL)
    return "\n".join(block.strip() for block in lua_blocks) if lua_blocks else response_text.strip()


def process_batch_output(
    client: Any,
    output_file_id: str,
    out_folder: str = "deeper"
) -> None:
    """
    Process batch API output file and extract Lua code.
    
    This function downloads the batch output file, extracts Lua code from
    responses, and saves them to organized files.
    
    Args:
        client: OpenAI client instance
        output_file_id: File ID of the batch output
        out_folder: Base folder for output files
    """
    try:
        print(f"Fetching batch output file: {output_file_id}")

        # Retrieve file content
        response = client.files.content(output_file_id)

        try:
            file_content = response.read().decode("utf-8")
        except Exception as e:
            print(f"Error decoding response: {e}")
            return

        print("Processing batch results...")

        for i, line in enumerate(file_content.strip().split("\n")):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON line {i + 1}: {e}")
                continue

            # Extract response content
            raw_response_text = (
                entry.get("response", {})
                     .get("body", {})
                     .get("choices", [{}])[0]
                     .get("message", {})
                     .get("content", "")
                     .strip()
            )
            
            lua_code = extract_lua_code(raw_response_text)
            if not lua_code:
                print(f"Warning: No content in response for {entry.get('custom_id', 'unknown')}")
                continue

            # Parse custom_id to determine output path
            custom_id = entry.get("custom_id", "unknown__unknown__output.lua")
            parts = custom_id.split("__")
            if len(parts) == 3:
                _, api_name, lua_filename = parts
            else:
                print(f"Warning: Invalid custom_id format: {custom_id}")
                continue

            # Create output directory structure
            api_dir = os.path.join(out_folder, api_name)
            os.makedirs(api_dir, exist_ok=True)

            # Write Lua code to file
            lua_filepath = os.path.join(api_dir, lua_filename)
            with open(lua_filepath, "w", encoding="utf-8") as lua_file:
                lua_file.write(lua_code)

            print(f"Stored converted Lua code: {lua_filepath}")

        print("Batch processing complete.")

    except Exception as e:
        print(f"Error processing batch output: {e}")


def check_batch_results(
    batch_id: str,
    out_folder: str = "deeper/round1",
    check_interval: int = 10
) -> Optional[str]:
    """
    Check batch job status and process results when complete.
    
    This function polls the batch job status and automatically processes
    the results when the batch completes.
    
    Args:
        batch_id: Batch job ID
        out_folder: Output folder for processed results
        check_interval: Seconds to wait between status checks
        
    Returns:
        Output file ID if successful, None otherwise
    """
    import time
    
    client = get_openai_client()
    
    while True:
        try:
            batch_info = client.batches.retrieve(batch_id)
            status = batch_info.status
            print(f"Batch Status: {status}")

            if status == "completed":
                output_file_id = batch_info.output_file_id
                
                if not output_file_id:
                    print("Error: No output file available for this batch.")
                    return None

                print(f"Batch completed! Downloading output file: {output_file_id}")
                process_batch_output(client, output_file_id, out_folder=out_folder)
                return output_file_id

            elif status in ["failed", "expired", "cancelled"]:
                print(f"Batch job failed or was cancelled. Status: {status}")
                return None

        except Exception as e:
            print(f"Error retrieving batch status: {e}")

        print(f"Waiting for batch results... Retrying in {check_interval} seconds.")
        time.sleep(check_interval)


def create_batch_from_jsonl(
    jsonl_file: str,
    job: str = "lua_fuzzing_conversion"
) -> Optional[str]:
    """
    Create a batch job from a JSONL file.
    
    Args:
        jsonl_file: Path to JSONL file containing batch requests
        job: Job identifier for metadata
        
    Returns:
        Batch ID if successful, None otherwise
    """
    client = get_openai_client()
    
    try:
        upload_response = client.files.create(
            file=open(jsonl_file, "rb"),
            purpose="batch"
        )
        file_id = upload_response.id
        print(f"File uploaded with ID: {file_id}")

        batch_response = client.batches.create(
            input_file_id=file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"job": job}
        )
        print(f"Batch job created with ID: {batch_response.id}")
        return batch_response.id
    except Exception as e:
        print(f"Error creating batch: {e}")
        return None

