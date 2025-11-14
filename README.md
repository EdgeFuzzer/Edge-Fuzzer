# EdgeFuzzer

## Introduction 

This repository includes the artifacts of EdgeFuzzer fuzzing framework provided by our research group.

## Overview

EdgeFuzzer is designed to automatically discover vulnerabilities in Edge Driver (on-hub drivers/integrations) APIs by:

- Generating fuzzing test cases using LLM models
- Executing test cases against the Edge Driver APIs
- Analyzing execution logs for potential vulnerabilities
- Iteratively refining test cases based on previous results

## Required Device/Software

EdgeFuzzer uses a dual-end monitoring system that requires specific hardware and software components for fuzzing SmartThings hub Zigbee APIs(example in this repo). The following are the minimum requirements:

### Hardware Requirements

- **PC/Workstation**: A computer capable of running Python 3.8+ and connecting to the nRF52840 dongle via USB
- **[SmartThings/Aeotec Hub v2](https://www.samsung.com/us/smartthings/hub/aeotec-smart-home-hub-2-sku-207025/)**: The target SmartThings hub for fuzzing Edge Driver APIs
- **[nRF52840 MDK USB Dongle](https://wiki.makerdiary.com/nrf52840-mdk-usb-dongle/)**: USB dongle with paired firmware for Zigbee communication and monitoring

### Software Requirements

- **[nRF Connect for Desktop](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-Desktop/Download)**: Nordic Semiconductor's desktop application for managing and configuring the nRF52840 dongle
- **SmartThings CLI**: Command-line interface for interacting with Edge Drivers (see Installation section)
- **Python 3.8+**: Required runtime environment (see Installation section)


## Architecture

EdgeFuzzer follows a modular architecture with the following components:

```
Edge-Fuzzer/
├── main.py                    # Main entry point for the fuzzing framework
├── __init__.py                # Package initialization
├── requirements.txt            # Python dependencies
├── dongle_firmware.uf2         # Firmware for nRF52840 dongle
├── README.md                   # This file
├── core/                       # Core fuzzing engine
│   ├── __init__.py
│   ├── fuzzer.py              # Main fuzzing orchestrator
│   └── connection_manager.py  # Socket communication with hub
├── generators/                 # Test case generators
│   ├── __init__.py
│   ├── gpt_generator.py       # OpenAI GPT-based generation
│   ├── rag_generator.py        # RAG-based generation with FAISS
│   └── prompt_templates.py     # Standardized prompt templates
├── discovery/                  # API discovery and analysis
│   ├── __init__.py
│   ├── api_extractor.py       # Extract API docs and source code
│   └── gpt_analyzer.py         # GPT-based API analysis
├── deeper/                     # Advanced multi-round fuzzing
│   ├── __init__.py
│   ├── batch_processor.py      # Batch API processing
│   └── deeper_runtime.py      # Multi-round fuzzing runtime
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── logger.py              # Logging utilities
│   ├── file_utils.py           # File I/O operations
│   ├── case_extractor.py      # Test case extraction
│   ├── json_processor.py      # JSON processing utilities
│   └── lua_dependency.py      # Lua dependency management
├── config/                     # Configuration
│   ├── __init__.py
│   ├── api_config.py          # API and function mappings
│   └── constants.py           # Framework constants
└── vul_reports/                # Vulnerability reports
    └── Homey_vul_report.pdf   # Example vulnerability report
```

**Workflow:**
1. **API Discovery**: Extract API documentation and source code
2. **Test Generation**: Use LLM models to generate fuzzing test cases
3. **Execution**: Send test cases to SmartThings Edge Driver hub
4. **Log Analysis**: Analyze execution logs for vulnerabilities
5. **Iteration**: Refine test cases based on previous results

## Installation

### Prerequisites

Before installing EdgeFuzzer, ensure you have:

- **Python**: Version 3.8 or higher
- **SmartThings CLI**: Required for interacting with Edge Drivers
  - Install via npm: `npm install -g @smartthings/cli`
  - Or download from [SmartThings Developer Portal](https://github.com/SmartThingsCommunity/smartthings-cli)
- **API Keys**:
  - **OpenAI API key**: Required for GPT-based test case generation

### Hardware Setup

1. **Connect nRF52840 Dongle**: 
   - Connect the nRF52840 MDK USB Dongle to your PC via USB
   - Install the paired firmware (`dongle_firmware.uf2`)
   - The firmware file is included in the repository root directory

2. **Configure SmartThings Hub**:
   - Ensure the SmartThings/Aeotec Hub v2 is powered on and connected to your network
   - Note the hub's IP address for configuration (see Configuration section)

### Software Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Edge-Fuzzer
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install SmartThings CLI** (if not already installed):
```bash
npm install -g @smartthings/cli
```

4. **Set up environment variables**:

   Option A - Using environment variables:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

   Option B - Using a `.env` file (recommended):
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your-openai-api-key
   ```
   
   The framework will automatically load variables from `.env` if `python-dotenv` is installed.

5. **Verify installation**:
   ```bash
   python main.py --help
   ```
   
   This should display the command-line help without errors.

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

#### Random Fuzzing Mode

Run fuzzing across multiple APIs and rounds:

```bash
python main.py \
    --api_name zdo/mgmt_bind_request \
    --test_file fuzzing_cases/zdo/mgmt_bind_request-0from_values.json \
    --hub_ip 192.168.1.100 \
    --fuzz_ip 192.168.1.101 \
    --fuzz_port 34567 \
    --round 0 \
    --total_round 10 \
    --llm_model gpt-4o-mini
```

#### Case Fuzzing Mode

Execute pre-generated test cases:

```bash
python main.py \
    --case_fuzzing True \
    --api_name zdo/mgmt_bind_request \
    --test_file fuzzing_cases/zdo/mgmt_bind_request.json \
    --hub_ip 192.168.1.100 \
    --fuzz_ip 192.168.1.101 \
    --fuzz_port 34567
```

#### Command-Line Arguments

- `--api_name`: API to fuzz (default: `zdo/mgmt_bind_request`)
- `--case_fuzzing`: Use case fuzzing mode (default: `True`)
- `--test_file`: Path to test case JSON file
- `--api_source`: Path to API source files (default: `./api_sources`)
- `--round`: Starting round number (default: `0`)
- `--total_round`: Total number of rounds (default: `10`)
- `--destination`: Output folder for generated cases (default: `./fuzzing_cases`)
- `--hub_ip`: IP address of SmartThings hub
- `--fuzz_ip`: IP address of fuzzing application
- `--fuzz_port`: Port number of hub for fuzzing
- `--llm_model`: LLM model to use (default: `gpt-4o`)
- `--vectorstore_path`: Path to FAISS vector store for RAG (default: `./vectorstore`)





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

EdgeFuzzer captures execution logs from the SmartThings Edge Driver and analyzes them for potential vulnerabilities. The log analysis process includes:

### Log Collection

Logs are automatically captured during test case execution and stored in the `logs/` directory, organized by API and function name.

### Log Analysis Methods

1. **Automated GPT Analysis**: Use GPT to analyze logs and identify vulnerabilities:
   ```python
   from generators.gpt_generator import validate_logs_with_gpt
   
   analysis = validate_logs_with_gpt(log_content, llm_model="gpt-4o")
   ```

2. **Manual Analysis**: Review logs for:
   - Error messages and stack traces
   - Memory-related issues
   - Unexpected behavior patterns
   - Security vulnerabilities

### Log Extraction

Extract relevant log content between markers:

```python
from utils.case_extractor import extract_log_content

extract_log_content(
    directory="logs/deeper/round1",
    start_marker="testing code generated by gpt...",
    end_marker="test finished"
)
```

### Iterative Refinement

Based on log analysis results, the framework can:
- Generate new test cases targeting identified vulnerabilities
- Refine existing test cases to bypass validation checks
- Focus on specific functions or APIs that show abnormal behavior

### API Key Issues

Ensure environment variables are set:

```bash
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```
