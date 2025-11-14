"""
File Utilities Module

This module provides file operations and data writing utilities for the
fuzzing framework, including JSON, HTML, YAML, and JSONL file handling.
"""

import os
import json
from utils.logger import FileLogger


def write_in_path(json_data: str, path: str) -> None:
    """
    Write JSON data to a file path.
    
    Creates the directory structure if it doesn't exist and writes
    the JSON data to a .json file.
    
    Args:
        json_data: JSON string to write
        path: File path (without extension)
    """
    try:
        os.makedirs(os.path.dirname(f'{path}.json'), exist_ok=True)
        FileLogger(f'{path}.json', level='info').logger.info(str(json_data))
    except Exception as msg:
        FileLogger('error.log', level='error', 
                  fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                  ).logger.error(msg)


def write_in_json(json_data: dict, path: str) -> None:
    """
    Write a Python dictionary as JSON to a file.
    
    Args:
        json_data: Dictionary to write as JSON
        path: File path (without extension)
    """
    try:
        os.makedirs(os.path.dirname(f'{path}.json'), exist_ok=True)
        with open(f'{path}.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)
    except Exception as msg:
        FileLogger('error.log', level='error',
                  fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                  ).logger.error(msg)


def write_in_html(html_data: str, path: str) -> None:
    """
    Write HTML data to a file.
    
    Args:
        html_data: HTML string to write
        path: File path (without extension)
    """
    try:
        FileLogger(f'{path}.html', level='info').logger.info(str(html_data))
    except Exception as msg:
        FileLogger('error.log', level='error',
                  fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                  ).logger.error(msg)


def write_in_yml(yml_data: str, path: str) -> None:
    """
    Write YAML data to a file.
    
    Args:
        yml_data: YAML string to write
        path: File path (without extension)
    """
    with open(f'{path}.yml', 'w', encoding='utf-8') as f:
        f.write(yml_data)


def write_in_jsonl(json_data: str, path: str) -> None:
    """
    Write JSON data to a JSONL file (one JSON object per line).
    
    Args:
        json_data: JSON string to write
        path: File path (without extension)
    """
    try:
        FileLogger(f'{path}.jsonl', level='info').logger.info(str(json_data))
    except Exception as msg:
        FileLogger('error.log', level='error',
                  fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                  ).logger.error(msg)


def check_dir(mypath: str) -> None:
    """
    Check if a directory exists and create it if it doesn't.
    
    Args:
        mypath: Directory path to check/create
    """
    if not os.path.exists(mypath):
        os.makedirs(mypath)

