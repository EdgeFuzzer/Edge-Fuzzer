"""
Prompt Templates Module

This module contains standardized prompt templates for generating fuzzing
test cases using various LLM models. The templates follow consistent
fuzzing policies and formatting requirements.
"""


def get_base_fuzzing_prompt() -> str:
    """
    Get the base fuzzing policy instructions.
    
    Returns:
        String containing the base fuzzing policies and instructions
    """
    return """
        ### Instruction ###
        1. Fuzzing Policies
        - Changing Argument Values: 
            -- For arguments checked by data types, include range extremes (e.g., minimum and maximum) and random valid values.
            -- For string-type arguments, alter lengths to potentially trigger buffer overflows.
            -- Provide empty strings to test for uninitialized reads or null-pointer dereferences.
            -- For arrays, sets, or bags, supply NULL or a single-element container to provoke out-of-bounds or null-pointer issues.
        - Changing Argument Types:  
            -- If a function does not invoke a type check (e.g., data_types.validate_or_build_type()), provide arguments in unexpected data types.
        - Changing the Number of Arguments:  
            -- For a function requiring n arguments, generate test cases with n+1, n-1, and 0 arguments.
        
        2. Analysis Steps
        - List all API functions from the specification (static methods and instance methods).
        - Locate each function's source code snippet in the provided Lua code.
        - Check whether each function calls data_types.validate_or_build_type() for argument validation.
        - Generate at least two fuzzing cases per function to explore potential vulnerabilities.
        
        3. Test Case Format
        - A JSON object includes all fuzzing test cases. For each fuzzing test case, it includes:
            -- "Test_Case": A unique integer identifier.
            -- "API_Name": Derived from the original function name, converting, for example, st.zigbee.zdo.BindRequest to zdo/mgmt_bind_request.
            -- "Function_Name": The actual Lua function name.
            -- "Description": A short explanation of the fuzzing goal.
            -- "Code_Snippets": One or more function-call strings showing mutated arguments.
            -- Optionally, "Pre-operation_Python" if you need to define variables or data in Python first (e.g., large strings).
        
        4. Additional Notes
        - Avoid direct mutations of parameters inside function calls (e.g., "deserialize(string.rep('A', 10^6))"). Instead, use a "Pre-operation_Python" step to define large inputs (e.g., "temp = 'A'*10^6"), then call the function with that variable.
        - Generate test cases only for the functions present in the provided specification.
        - The environment disables load() and loadfile(), so do not reference them.
        - Your response must strictly rely on the text provided (do not invent new APIs or code).
    """


def get_test_case_example() -> str:
    """
    Get an example test case in JSON format.
    
    Returns:
        String containing an example test case
    """
    return """
        Example:
        ```json
        [
            {{
                "Test_Case": 1,
                "API_Name": "zdo/mgmt_bind_request",
                "Function_Name": "from_values",
                "Description": "Call from_values with appropriate values for start_index.",
                "Code_Snippets": [
                    "MgmtBindRequest.from_values({{}}, 0)", 
                    "MgmtBindRequest.from_values({{}}, 1)",
                    "MgmtBindRequest.from_values({{}}, 2)"
                ]
            }}
        ]
        ```
    """


def get_case_generation_prompt(api_doc: str, api_code: str, api_name_w_function: str) -> str:
    """
    Generate a complete prompt for test case generation.
    
    Args:
        api_doc: API documentation text
        api_code: API source code in Lua
        api_name_w_function: API name with function identifier
        
    Returns:
        Complete prompt string for LLM
    """
    base_prompt = get_base_fuzzing_prompt()
    example = get_test_case_example()
    
    return f"""
        You are a helpful Testing Assistant specializing in black-box testing and fuzzing. 
        Please use the following instructions to generate fuzzing test cases strictly based on 
        the provided API documentation and Lua source code.
        It is imperative that your responses be strictly based on the text provided. 
        
        {base_prompt}
        
        {example}
        
        ### Context ###
        
        API Document:
        {api_doc}
        
        API Source Code:
        {api_code}
        
        Question:
        According to the API specification and the source code in Lua, please generate JSON-formatted 
        fuzzing test cases as much as you can for the function {api_name_w_function} based on the 
        above instructions.
        
        Answer:
    """


def get_claude_case_generation_prompt(api_doc: str, api_code: str, api_name_w_function: str) -> str:
    """
    Generate a prompt specifically formatted for Claude API.
    
    This version includes the run_test_case() function wrapper that Claude
    generators should use.
    
    Args:
        api_doc: API documentation text
        api_code: API source code in Lua
        api_name_w_function: API name with function identifier
        
    Returns:
        Complete prompt string for Claude API
    """
    return f"""
        You are a helpful Testing Assistant specializing in black-box testing and fuzzing. 
        Please use the following instructions to generate fuzzing test cases strictly based on 
        the provided API documentation and Lua source code.
        It is imperative that your responses be strictly based on the text provided. 
        
        ### Instruction ###
        1. Fuzzing Policies
        - Changing Argument Values: 
            -- For arguments checked by data types, include range extremes (e.g., minimum and maximum) and random valid values.
            -- For string-type arguments, alter lengths to potentially trigger buffer overflows.
            -- Provide empty strings to test for uninitialized reads or null-pointer dereferences.
            -- For arrays, sets, or bags, supply NULL or a single-element container to provoke out-of-bounds or null-pointer issues.
        - Changing Argument Types:  
            -- If a function does not invoke a type check, provide arguments in unexpected data types.
        - Changing the Number of Arguments:  
            -- For a function requiring n arguments, generate test cases with n+1, n-1, and 0 arguments.
        
        2. Analysis Steps
        - List all API functions from the specification (static methods and instance methods).
        - Locate each function's source code snippet in the provided Lua code.
        - Check whether each function calls data_types.validate_or_build_type() for argument validation.
        - Generate fuzzing cases to explore potential vulnerabilities.
        
        3. Test Case Format
        - A JSON object includes all fuzzing test cases. For each fuzzing test case, it includes:
            -- "Code_Snippets": One or more function-call strings showing mutated arguments.
        - run_test_case() function has already been implement as below, you don't have to use this function.
        ```lua
        local function run_test_case(func, ...)
            local success, result = pcall(func, ...)
            if not success then
                print("Test Case: Error:", result)
            else
                print("Test Case: Success:", result)
            end
        end
        ```

        Example of fuzzing cases for from_values() function:
        ```json
        [
            {{
                "Code_Snippets": [
                    "run_test_case(MgmtBindRequest.from_values, {{}}, 0)"
                    "run_test_case(MgmtBindRequest.from_values, {{}}, 1)",
                    "run_test_case(MgmtBindRequest.from_values, {{}}, 2)"
                ]
            }}
        ]
        ```
        
        4. Additional Notes
        - The environment disables load() and loadfile(), so do not reference them.
        - Your response must strictly rely on the text provided (do not invent new APIs or code).
        - Please only include the generated fuzzing cases with json format in your response.
        
        ### Context ###
        
        API Document:
        {api_doc}
        
        API Source Code:
        {api_code}
        
        Question:
        According to the API specification and the source code in Lua, please generate JSON-formatted 
        fuzzing test cases as much as you can for the function {api_name_w_function} based on the 
        above instructions.
        
        Answer:
    """


def get_second_round_prompt(
    api_doc: str,
    api_code: str,
    fuzzing_cases_content: str,
    fuzzing_results_contents: str,
    api: str,
    func: str
) -> str:
    """
    Generate a prompt for second round fuzzing based on previous results.
    
    Args:
        api_doc: API documentation text
        api_code: API source code in Lua
        fuzzing_cases_content: Content from previous fuzzing cases
        fuzzing_results_contents: Analysis results from previous round
        api: API name
        func: Function name
        
    Returns:
        Complete prompt string for second round generation
    """
    return f"""
        You are a helpful Testing Assistant specializing in black-box testing. Please use the 
        following instructions to re-generate fuzzing test cases strictly based on the provided 
        information.
        It is imperative that your responses be strictly based on the text provided. 
        
        ### Instruction ###
        1. Fuzzing Policies
        - Changing Argument Values: 
            -- For arguments checked by data types, include range extremes (e.g., minimum and maximum) and random valid values.
            -- For string-type arguments, alter lengths to potentially trigger buffer overflows.
            -- Provide empty strings to test for uninitialized reads or null-pointer dereferences.
            -- For arrays, sets, or bags, supply NULL or a single-element container to provoke out-of-bounds or null-pointer issues.
        - Changing Argument Types:  
            -- If a function does not invoke a type check (e.g., data_types.validate_or_build_type()), provide arguments in unexpected data types.
        - Changing the Number of Arguments:  
            -- For a function requiring n arguments, generate test cases with n+1, n-1, and 0 arguments.
        
        2. Test Case Format
        - A JSON object includes all fuzzing test cases. For each fuzzing test case, it includes:
            -- "Test_Case": A unique integer identifier.
            -- "API_Name": Derived from the original function name, converting, for example, st.zigbee.zdo.BindRequest to zdo/mgmt_bind_request.
            -- "Function_Name": The actual Lua function name.
            -- "Description": A short explanation of the fuzzing goal.
            -- "Code_Snippets": One or more function-call strings showing mutated arguments.
            -- Optionally, "Pre-operation_Python" if you need to define variables or data in Python first (e.g., large strings).
        
        {get_test_case_example()}
        
        4. Additional Notes
        - Avoid direct mutations of parameters inside function calls (e.g., "deserialize(string.rep('A', 10^6))"). Instead, use a "Pre-operation_Python" step to define large inputs (e.g., "temp = 'A'*10^6"), then call the function with that variable.
        - Generate test cases only for the functions present in the provided specification.
        - The environment disables load() and loadfile(), so do not reference them.
        - Your response must strictly rely on the text provided (do not invent new APIs or code).
        
        ### Context ###
        
        API Document:
        {api_doc}
        
        API Source Code:
        {api_code}
        
        Previous Fuzzing Cases:
        {fuzzing_cases_content}
        
        Potential Fuzzing Directions:
        {fuzzing_results_contents}
        
        Question:
        According to the context above, please provide 15 JSON-formatted fuzzing test cases for 
        the function {func} of the API {api}.
        
        Answer:
    """

