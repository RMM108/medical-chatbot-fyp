#!/usr/bin/env python3
"""
Launcher for Medical Training Chatbot
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.chatbot import main

if __name__ == "__main__":
    main()
