"""
Lua Dependency Module

This module provides utilities for managing Lua code dependencies,
extracting function references, and combining Lua files with their
dependencies.
"""

import os
import re
import json
import queue
from typing import Dict, List, Tuple, Optional


def read_lua_file(file_path: str) -> str:
    """
    Read a Lua file and return its content.
    
    Args:
        file_path: Path to Lua file
        
    Returns:
        File content as string
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def write_files(file_path: str, content: str) -> None:
    """
    Append content to a file.
    
    Args:
        file_path: Path to file
        content: Content to append
    """
    with open(file_path, "a", encoding="utf-8") as file:
        file.write(f"{content}")


def find_references(lua_code: str, module_name: str) -> List[str]:
    """
    Find all references to a module in Lua code.
    
    Args:
        lua_code: Lua source code
        module_name: Module name to search for
        
    Returns:
        List of matching references
    """
    pattern = rf'{re.escape(module_name)}\.[\w_]+'
    matches = re.findall(pattern, lua_code)
    return matches


def extract_local_requirements(lua_code: str) -> List[Tuple[str, str]]:
    """
    Extract local require statements from Lua code.
    
    Args:
        lua_code: Lua source code
        
    Returns:
        List of tuples (variable_name, module_path)
    """
    pattern = r'local\s+(\w+)\s*=\s*require\s*["\']([\w\.]+)["\']'
    matches = re.findall(pattern, lua_code)
    return matches


def extract_function_block(lua_code: str, function_name: str) -> Optional[str]:
    """
    Extract a function block from Lua code.
    
    Args:
        lua_code: Lua source code
        function_name: Function name to extract
        
    Returns:
        Function block as string, or None if not found
    """
    # Try different function definition patterns
    pattern = rf"{re.escape(function_name)}\s*=\s*function\s*\(.*?\)\s*\n(.*?)^end\s*$"
    pattern_1 = rf"function\s+{re.escape(function_name)}\s*\(.*?\)\s*\n(.*?)^end\s*$"
    
    match = re.search(pattern, lua_code, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(0)
    
    match_1 = re.search(pattern_1, lua_code, re.MULTILINE | re.DOTALL)
    if match_1:
        return match_1.group(0)
    
    return None


def extract_dependencies(unique: str, dependencies_obj: Dict) -> List[str]:
    """
    Extract all dependencies for a given module recursively.
    
    Args:
        unique: Module name
        dependencies_obj: Dictionary mapping files to their dependencies
        
    Returns:
        List of dependency module names
    """
    dependencies = []
    q = queue.Queue()

    unique = unique.split('.')[1] if '.' in unique else unique
    q.put(unique)
    
    while not q.empty():
        temp = q.get()
        if f'{temp}.lua' in dependencies_obj.keys():
            dependencies.append(temp)
            value_array = dependencies_obj[f'{temp}.lua']
            for value in value_array:
                q.put(value[0])

    return dependencies


def parse_transmitting_dependency(
    parent_folder: str,
    depen_dic: List[str],
    dependencies_obj: Dict
) -> Dict[str, List[str]]:
    """
    Parse and extract dependencies for a list of modules.
    
    Args:
        parent_folder: Base folder path
        depen_dic: List of dependency module names
        dependencies_obj: Dictionary mapping files to their dependencies
        
    Returns:
        Dictionary mapping file paths to their referenced functions
    """
    return_obj = {}
    
    for depen in depen_dic:
        key = f'{depen}.lua'
        value_array = dependencies_obj.get(key, [])
        
        for value in value_array:
            unique = value[0]
            folder = value[1]

            sub_key = f'{unique}.lua'
            if sub_key in dependencies_obj.keys():
                target_lua_file = f'{parent_folder}/{folder.replace(".", "/")}.lua'
                code_content = read_lua_file(target_lua_file)

                reference_functions = find_references(code_content, unique)
                unique_functions = list(set(reference_functions))
                return_obj[target_lua_file] = unique_functions
            else:
                target_lua_file = f'{parent_folder}/{folder.replace(".", "/")}.lua'
                if os.path.exists(target_lua_file):
                    code_content = read_lua_file(target_lua_file)
                    reference_functions = find_references(code_content, unique)
                    unique_functions = list(set(reference_functions))
                    return_obj[target_lua_file] = unique_functions

    return return_obj


def generate_new_combine_lua(
    parent_folder: str,
    sub_folder: str,
    filename: str,
    extract_depen_obj: Dict[str, List[str]]
) -> None:
    """
    Generate a new Lua file with dependencies inlined.
    
    Args:
        parent_folder: Base folder path
        sub_folder: Subfolder path
        filename: Lua filename
        extract_depen_obj: Dictionary mapping file paths to function lists
    """
    destination = f'{parent_folder}/{sub_folder}/{filename}'
    original_code = read_lua_file(destination)

    combine_code = ''

    for key in extract_depen_obj.keys():
        if not os.path.exists(key):
            continue
            
        code_content = read_lua_file(key)
        functions = extract_depen_obj[key]

        for func in functions:
            temp_func = func
            if '_utils' in func:
                temp_func = f'utils.{func.split(".")[1]}'
                
            extract_function = extract_function_block(code_content, temp_func)
            if extract_function:
                extract_function = extract_function.replace(temp_func, func)
                combine_code += f"\n{extract_function}"
    
    write_code = f'''
    ------------------import functions begin------------------\n
    {combine_code}\n
    ------------------import functions end------------------\n

    {original_code}
    '''
    write_path = f'{parent_folder}/{sub_folder}/{filename.split(".")[0]}_new.lua'
    write_files(write_path, write_code)


def get_target_code(
    parent_folder: str,
    sub_folder: str,
    filename: str,
    dependencies_file: str
) -> None:
    """
    Extract and combine dependencies for a target Lua file.
    
    Args:
        parent_folder: Base folder path
        sub_folder: Subfolder path
        filename: Target Lua filename
        dependencies_file: Path to JSON file containing dependency mappings
    """
    destination = f'{parent_folder}/{sub_folder}/{filename}'

    # Load dependencies
    dependencies_content = read_lua_file(dependencies_file)
    dependencies_obj = json.loads(dependencies_content.rstrip())

    if filename not in dependencies_obj.keys():
        print('There are no dependencies, no need to extend...')
        return

    dependencies_array = dependencies_obj[filename]

    code_content = read_lua_file(destination)
    extract_depen_obj = {}
    
    for module, reference in dependencies_array:
        reference_functions = find_references(code_content, module)
        unique_functions = list(set(reference_functions))

        folder_flag = False
        sub_destination = f'{parent_folder}/{reference.replace(".", "/")}'
        if os.path.isdir(sub_destination):
            folder_flag = True

        for unique in unique_functions:
            depen_dic = extract_dependencies(unique, dependencies_obj)
            
            if len(depen_dic) <= 0:
                if folder_flag:
                    target_lua_file = f'{sub_destination}/init.lua'
                else:
                    target_lua_file = f'{sub_destination}.lua'
                
                if target_lua_file not in extract_depen_obj.keys():
                    extract_depen_obj[target_lua_file] = [unique]
                else:
                    extract_depen_obj[target_lua_file].append(unique)
            else:
                combo = f'{reference.replace(".", "/")}/{unique.split(".")[1]}.lua'
                target_lua_file = f'{parent_folder}/{combo}'
                extract_depen_obj[target_lua_file] = []
                return_obj = parse_transmitting_dependency(parent_folder, depen_dic, dependencies_obj)
                
                for key in return_obj:
                    if key not in extract_depen_obj.keys():
                        extract_depen_obj[key] = return_obj[key]
                    else:
                        values = return_obj[key]
                        for val in values:
                            if val not in extract_depen_obj[key]:
                                extract_depen_obj[key].append(val)
    
    generate_new_combine_lua(parent_folder, sub_folder, filename, extract_depen_obj)


def generate_dependency_json(folder: str, output_file: str) -> None:
    """
    Generate a JSON file mapping Lua files to their dependencies.
    
    Args:
        folder: Folder to scan for Lua files
        output_file: Path to output JSON file
    """
    requirement_local = {}

    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.lua'):
                file_path = os.path.join(root, file)
                lua_code = read_lua_file(file_path)
                local_requires = extract_local_requirements(lua_code)

                if len(local_requires) > 0:
                    requirement_local[file] = local_requires
    
    write_files(output_file, json.dumps(requirement_local))
    print(f"Generated dependency JSON with {len(requirement_local.keys())} files")

