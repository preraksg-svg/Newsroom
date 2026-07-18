with open('system_orchestrator.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if "signal['content']" in line or 'signal["content"]' in line:
            print(f'{idx+1}: {line.strip()}')
