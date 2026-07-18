with open('zapway_publisher.py', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if 'def publish_to_zapway' in line or 'progress' in line or 'update' in line or 'log' in line:
            print(f'{idx+1}: {line.strip()}')
