#!/bin/bash

newtask() {
  echo "🚀 Routing task: $*"
  echo "=" * 50
  
  # Get the compiled prompt from the router
  python codex_router.py --task "$*" --json | tee /tmp/codex_prompt.json
  
  # Extract and copy the compiled prompt to clipboard
  python -c "
import json
import subprocess
import sys

try:
    with open('/tmp/codex_prompt.json', 'r') as f:
        data = json.load(f)
    
    prompt = data.get('compiled_prompt', '')
    if prompt:
        # Try to copy to clipboard
        try:
            subprocess.run(['pbcopy'], input=prompt, text=True, check=True)
            print('✅ Prompt copied to clipboard (macOS)')
        except:
            try:
                subprocess.run(['xclip', '-selection', 'clipboard'], input=prompt, text=True, check=True)
                print('✅ Prompt copied to clipboard (Linux)')
            except:
                print('📋 Prompt (copy manually):')
                print('-' * 50)
                print(prompt)
                print('-' * 50)
    else:
        print('❌ No prompt generated')
        
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"
  
  echo ""
  echo "🎯 Next steps:"
  echo "1. Open a new Codex chat"
  echo "2. Paste the compiled prompt (already in clipboard)"
  echo "3. Start working with the specialized agent!"
  echo ""
  echo "💡 The prompt includes mode-specific knowledge and constraints"
}

# Export the function so it can be used in the current shell
export -f newtask

echo "🚀 newtask helper loaded!"
echo "Usage: newtask 'Plain English task description'"
echo "Example: newtask 'Design a responsive navigation component'"
