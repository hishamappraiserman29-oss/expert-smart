"""
Helper script to start bridge_api server with stdout flushing
"""
import sys, os, subprocess

# Clear any .pyc caches
import glob
for f in glob.glob(os.path.join(os.path.dirname(__file__), '__pycache__', 'bridge_api*')):
    os.remove(f)
    print(f'Cleared: {f}')

# Start server
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.execv(sys.executable, [sys.executable, '-u', 'bridge_api.py'])
