import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge_api as api
print('Registered routes:')
for rule in api.app.url_map.iter_rules():
    print(f'  {rule.rule!r:40} methods={sorted(rule.methods)}')
