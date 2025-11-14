"""
GPT Analyzer Module

This module provides utilities for sending API documentation to GPT
for analysis and identifying fuzzing candidates.
"""

import os
import tiktoken
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from config.constants import ENV_OPENAI_API_KEY


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: Text to count tokens for
        model: Model name for tokenization
        
    Returns:
        Number of tokens
        
    Raises:
        ImportError: If tiktoken package is not installed
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to approximate counting
        return len(text.split())


def split_content(content: str, max_tokens: int = 30000) -> list:
    """
    Split content into chunks that fit within token limits.
    
    Args:
        content: Content to split
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List of content chunks
    """
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    # Split by newlines to maintain some structure
    lines = content.split('\n')
    
    for line in lines:
        line_tokens = count_tokens(line)
        
        if current_tokens + line_tokens > max_tokens:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line + "\n"
            current_tokens = line_tokens
        else:
            current_chunk += line + "\n"
            current_tokens += line_tokens
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def read_prompt_file(file_path: str) -> Optional[str]:
    """
    Read the prompt file content.
    
    Args:
        file_path: Path to prompt file
        
    Returns:
        File content as string, or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading prompt file: {str(e)}")
        return None


def send_to_gpt(
    prompt_content: str,
    model: str = "gpt-4.1-2025-04-14",
    temperature: float = 0.4,
    max_tokens: int = 30000
) -> Optional[str]:
    """
    Send the prompt to GPT and get the response.
    
    This function handles large prompts by splitting them into chunks
    and combining the responses.
    
    Args:
        prompt_content: Prompt content to send
        model: GPT model to use
        temperature: Temperature parameter
        max_tokens: Maximum tokens in response
        
    Returns:
        Combined response from GPT, or None if error
        
    Raises:
        ImportError: If openai package is not installed
        ValueError: If API key is not set
    """
    if OpenAI is None:
        raise ImportError("openai package required. Install with: pip install openai")
    
    api_key = os.environ.get(ENV_OPENAI_API_KEY)
    if not api_key:
        raise ValueError(f"{ENV_OPENAI_API_KEY} environment variable not set")
    
    client = OpenAI(api_key=api_key)
    
    try:
        # Split the content into manageable chunks
        chunks = split_content(prompt_content)
        all_responses = []
        
        for i, chunk in enumerate(chunks):
            print(f"\nProcessing chunk {i+1}/{len(chunks)}...")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", 
                     "content": "You are a security-focused AI assistant analyzing API documentation "
                               "and source code for potential vulnerabilities. This is part of a larger "
                               "analysis, so focus on the specific content provided."},
                    {"role": "user", 
                     "content": f"This is chunk {i+1} of {len(chunks)}. Please analyze the following content:\n\n{chunk}"}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            chunk_response = response.choices[0].message.content
            print(f"\nResponse for chunk {i+1}:")
            print("-" * 80)
            print(chunk_response)
            print("-" * 80)
            
            all_responses.append(chunk_response)
        
        # Combine all responses
        return "\n\n".join(all_responses)
    except Exception as e:
        print(f"Error sending request to GPT: {str(e)}")
        return None


def save_response(response: str, output_file: str) -> None:
    """
    Save the GPT response to a file.
    
    Args:
        response: Response text to save
        output_file: Path to output file
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response)
        print(f"\nResponse saved to {output_file}")
    except Exception as e:
        print(f"Error saving response: {str(e)}")


def analyze_api_documentation(
    prompt_file: str,
    output_file: str = "gpt_response.txt",
    model: str = "gpt-4.1-2025-04-14"
) -> Optional[str]:
    """
    Analyze API documentation using GPT.
    
    This is the main entry point for analyzing API documentation to
    identify fuzzing candidates.
    
    Args:
        prompt_file: Path to prompt file containing API documentation
        output_file: Path to save analysis results
        model: GPT model to use
        
    Returns:
        Analysis response from GPT, or None if error
    """
    # Read the prompt content
    prompt_content = read_prompt_file(prompt_file)
    if not prompt_content:
        return None
    
    # Send prompt to GPT and get response
    response = send_to_gpt(prompt_content, model=model)
    if not response:
        return None
    
    # Save the response
    save_response(response, output_file)
    return response

