# EdgeFuzzer

## Introduction 

This repository includes the artifacts of EdgeFuzzer fuzzing framework provided by our research group.

## Overview

EdgeFuzzer is designed to automatically discover vulnerabilities in Edge Driver (on-hub drivers/integrations) APIs by:

- Generating fuzzing test cases using LLM models
- Executing test cases against the Edge Driver APIs
- Analyzing execution logs for potential vulnerabilities
- Iteratively refining test cases based on previous results

## Architecture



## Installation

### Prerequisites





## Configuration

### API Configuration

Edit `config/api_config.py` to configure:

- Available APIs to fuzz (`FUZZING_API_CHOICES`)
- Functions for each API (`FUNC_SUM`)

### Constants

Edit `config/constants.py` to set:

- Default paths for API sources, logs, and output
- Network configuration (hub IP, fuzzing app IP/port)
- Default LLM models and parameters

## Usage

### Basic Fuzzing





## Fuzzing Policies

The framework follows these fuzzing policies:

1. **Changing Argument Values**:
   - Range extremes (min/max) for typed arguments
   - Variable-length strings for buffer overflow testing
   - Empty values for null pointer dereference testing
   - Edge cases for arrays/containers

2. **Changing Argument Types**:
   - Unexpected data types when type checking is absent
   - Type coercion attempts

3. **Changing Number of Arguments**:
   - n+1, n-1, and 0 arguments for functions requiring n arguments



## Test Case Format

Test cases are stored in JSON format:

```json
[
    {
        "Test_Case": 1,
        "API_Name": "zdo/mgmt_bind_request",
        "Function_Name": "from_values",
        "Description": "Call from_values with edge case values",
        "Code_Snippets": [
            "MgmtBindRequest.from_values({}, 0)",
            "MgmtBindRequest.from_values({}, -1)",
            "MgmtBindRequest.from_values({}, 999999)"
        ],
        "Pre-operation_Python": null
    }
]
```

## Log Analysis



## Module Documentation

### Core Modules







### API Key Issues

Ensure environment variables are set:

```bash
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```
