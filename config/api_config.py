"""
API Configuration Module

This module consolidates all API choices and function mappings used across
the fuzzing framework. It provides a centralized configuration for:
- Available APIs to fuzz
- Functions associated with each API
- API naming conventions
"""

# List of APIs available for fuzzing
# Format: 'module/submodule' (e.g., 'zdo/mgmt_bind_request')
FUZZING_API_CHOICES = [
    'zdo/top_level_module',
    'zdo/bind_request',
    'zdo/bind_request_response',
    'zdo/mgmt_bind_request',
    'zdo/mgmt_bind_response',
    'buf/Buf',
    'buf/Writer',
    'buf/Reader',
    'socket/init',
    'socket/http',
    'socket/url'
]

# Mapping of API names to their associated functions
# Each API has a list of functions that can be fuzzed
# Format: 'api_name': ['function1()', 'function2()', ...]
FUNC_SUM = {
    'zdo/top_level_module': [
        "parse_zdo_command()"
    ],
    'zdo/bind_request': [
        "deserialize()",
        "from_values()",
        "get_fields()",
        "get_length()",
        "_serialize()",
        "pretty_print()"
    ],
    'zdo/bind_request_response': [
        "deserialize()",
        "from_values()",
        "get_fields()",
        "get_length()",
        "_serialize()",
        "pretty_print()"
    ],
    'zdo/mgmt_bind_request': [
        "from_values()",
        "deserialize()",
        "get_fields()",
        "get_length()",
        "_serialize()",
        "pretty_print()"
    ],
    'zdo/mgmt_bind_response': [
        "BindingTableListRecord:deserialize()",
        "BindingTableListRecord:from_values()",
        "deserialize()",
        "from_value()"
    ],
    'buf/Buf': [
        "init()",
        "size()",
        "tell()",
        "bit_tell()",
        "remain()",
        "bits_remain()",
        "seek()",
        "bit_seek()"
    ],
    'buf/Writer': [
        "init()",
        "pretty_print()",
        "write_int()",
        "write_u8()",
        "write_le_u16()",
        "write_be_u16()",
        "write_le_u24()",
        "write_be_u24()",
        "write_le_u32()",
        "write_be_u32()",
        "write_le_u40()",
        "write_be_u40()",
        "write_le_u48()",
        "write_be_u48()",
        "write_le_u56()",
        "write_be_u56()",
        "write_i8()",
        "write_le_i16()",
        "write_be_i16()",
        "write_le_i24()",
        "write_be_i24()",
        "write_le_i32()",
        "write_be_i32()",
        "write_le_i40()",
        "write_be_i40()",
        "write_le_i48()",
        "write_be_i48()",
        "write_le_i56()",
        "write_be_i56()",
        "write_bytes()",
        "write_bool()",
        "write_bits()"
    ],
    'buf/Reader': [
        "init()",
        "pretty_print()",
        "store()",
        "read_int()",
        "read_u8()",
        "read_le_u16()",
        "read_be_u16()",
        "read_le_u24()",
        "read_be_u24()",
        "read_le_u32()",
        "read_be_u32()",
        "read_le_u40()",
        "read_be_u40()",
        "read_le_u48()",
        "read_be_u48()",
        "read_le_u56()",
        "read_be_u56()",
        "read_i8()",
        "read_le_i16()",
        "read_be_i16()",
        "read_le_i24()",
        "read_be_i24()",
        "read_le_i32()",
        "read_be_i32()",
        "read_le_i40()",
        "read_be_i40()",
        "read_le_i48()",
        "read_be_i48()",
        "read_le_i56()",
        "read_be_i56()",
        "read_le_i64()",
        "read_be_i64()",
        "read_bytes()",
        "read_bool()",
        "read_bits()",
        "peek_u8()"
    ],
    'socket/init': [
        "bind()",
        "connect4()",
        "connect6()"
    ],
    'socket/http': [
        "open()",
        "request()",
        "genericform()"
    ],
    'socket/url': [
        "escape()",
        "unescape()",
        "parse()",
        "build()",
        "absolute()",
        "parse_path()",
        "build_path()"
    ]
}


def get_api_functions(api_name: str) -> list:
    """
    Get the list of functions for a given API.
    
    Args:
        api_name: The API name in format 'module/submodule'
        
    Returns:
        List of function names for the API, or empty list if API not found
    """
    return FUNC_SUM.get(api_name, [])


def is_valid_api(api_name: str) -> bool:
    """
    Check if an API name is valid (exists in the configuration).
    
    Args:
        api_name: The API name to validate
        
    Returns:
        True if the API is valid, False otherwise
    """
    return api_name in FUZZING_API_CHOICES

