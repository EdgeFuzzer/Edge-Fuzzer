"""
EdgeFuzzer - Main Entry Point

This is the main entry point for the EdgeFuzzer framework.
It provides a command-line interface for running fuzzing operations.
"""

import argparse
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.fuzzer import (
    random_fuzzing,
    case_fuzzing,
    create_argument_parser
)
from config.constants import (
    DEFAULT_HUB_IP,
    DEFAULT_FUZZ_IP,
    DEFAULT_FUZZ_PORT,
    DEFAULT_ROUND,
    DEFAULT_TOTAL_ROUNDS,
    DEFAULT_LLM_MODEL,
    DEFAULT_API_SOURCE_PATH,
    DEFAULT_FUZZING_CASES_PATH
)


def main():
    """
    Main entry point for the fuzzing framework.
    
    This function parses command-line arguments and executes the appropriate
    fuzzing mode (random fuzzing or case fuzzing).
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Execute fuzzing based on mode
    if args.case_fuzzing:
        print("Running case fuzzing mode...")
        case_fuzzing(args)
    else:
        print("Running random fuzzing mode...")
        random_fuzzing(args)


if __name__ == "__main__":
    main()

