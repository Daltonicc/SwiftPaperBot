#!/usr/bin/env python3
"""
Swift 논문 요약 슬랙봇 실행 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    main() 