#!/usr/bin/env python3
"""
Upload project files to GitHub via API (bypassing git push network issues)
"""
import os
import json
import base64
import subprocess
import sys

REPO = "Ran127127/gm-sentiment"

def run_gh(args):
    """Run gh command and return output"""
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def main():
    # Collect all files
    files = []
    skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv'}
    skip_exts = {'.pyc', '.pyo', '.db', '.sqlite3'}
    
    for root, dirs, filenames in os.walk('.'):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for f in filenames:
            if any(f.endswith(ext) for ext in skip_exts):
                continue
            
            filepath = os.path.join(root, f)
            # Normalize path (remove leading ./ and use forward slashes)
            relpath = os.path.relpath(filepath, '.').replace('\\', '/')
            files.append(relpath)
    
    print(f"Found {len(files)} files to upload")
    
    # Upload files one by one using Contents API
    success = 0
    failed = 0
    
    for i, filepath in enumerate(files):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # Base64 encode
            encoded = base64.b64encode(content).decode('utf-8')
            
            # Use gh api to create/update file
            # For the first file, we create initial commit
            # For subsequent files, we update
            message = f"Add {filepath}" if i > 0 else "Initial commit: GM China sentiment monitoring system"
            
            out, err, code = run_gh([
                "api",
                f"repos/{REPO}/contents/{filepath}",
                "-X", "PUT",
                "-f", f"message={message}",
                "-f", f"content={encoded}",
                "-q", ".commit.sha"
            ])
            
            if code == 0 and out:
                print(f"[{i+1}/{len(files)}] OK: {filepath}")
                success += 1
            else:
                print(f"[{i+1}/{len(files)}] FAILED: {filepath} - {err}")
                failed += 1
                
        except Exception as e:
            print(f"[{i+1}/{len(files)}] ERROR: {filepath} - {e}")
            failed += 1
    
    print(f"\nDone! Success: {success}, Failed: {failed}")
    print(f"View at: https://github.com/{REPO}")

if __name__ == "__main__":
    main()
