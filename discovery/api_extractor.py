"""
API Extractor Module

This module provides utilities for extracting API documentation and source
code from HTML and Lua files for analysis and fuzzing case generation.
"""

import os
import re
from typing import Optional


def extract_html_content(file_path: str) -> str:
    """
    Extract content from HTML files, removing HTML tags and formatting.
    
    Args:
        file_path: Path to HTML file
        
    Returns:
        Plain text content extracted from HTML
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            # Remove multiple spaces and newlines
            content = re.sub(r'\s+', ' ', content)
            return content.strip()
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"


def extract_lua_content(file_path: str) -> str:
    """
    Extract content from Lua files.
    
    Args:
        file_path: Path to Lua file
        
    Returns:
        Lua file content as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"


def process_directory(
    directory: str,
    output_file: str,
    docs_subfolder: str = "docs",
    code_subfolder: str = "code_exp"
) -> None:
    """
    Process all files in a directory and its subdirectories.
    
    This function extracts content from HTML documentation files and Lua
    source code files, then writes them to a single output file.
    
    Args:
        directory: Base directory to process
        output_file: Path to output file
        docs_subfolder: Subfolder name containing documentation (default: "docs")
        code_subfolder: Subfolder name containing Lua code (default: "code_exp")
    """
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("<folder_contents>\n")
        
        # Process docs directory
        docs_path = os.path.join(directory, docs_subfolder)
        if os.path.exists(docs_path):
            out.write("\n=== Documentation Files ===\n")
            for root, _, files in os.walk(docs_path):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        out.write(f"\n--- {file} ---\n")
                        out.write(extract_html_content(file_path))
                        out.write("\n")
        
        # Process lua_api_code_v12 directory
        lua_path = os.path.join(directory, code_subfolder)
        if os.path.exists(lua_path):
            out.write("\n=== Lua Source Code Files ===\n")
            for root, _, files in os.walk(lua_path):
                for file in files:
                    if file.endswith('.lua'):
                        file_path = os.path.join(root, file)
                        out.write(f"\n--- {file} ---\n")
                        out.write(extract_lua_content(file_path))
                        out.write("\n")

        out.write("</folder_contents>\n")


def extract_api_contents(
    base_dir: str,
    output_file: str = "api_contents.txt",
    docs_subfolder: str = "docs",
    code_subfolder: str = "code_exp"
) -> None:
    """
    Extract API contents from a directory structure.
    
    This is the main entry point for extracting API documentation and
    source code for analysis.
    
    Args:
        base_dir: Base directory containing API files
        output_file: Output file path
        docs_subfolder: Subfolder name for documentation
        code_subfolder: Subfolder name for Lua code
    """
    if not os.path.exists(base_dir):
        print(f"Error: Directory {base_dir} not found")
        return
    
    process_directory(base_dir, output_file, docs_subfolder, code_subfolder)
    print(f"Content extracted and saved to {output_file}")

