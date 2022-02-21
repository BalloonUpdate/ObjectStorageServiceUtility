import sys
import json
from file import File

temp = File(getattr(sys, '_MEIPASS', ''))
meta = temp('meta.json')
metadata = json.loads(meta.content) if meta.exists else {}

version = metadata.get('version', 'dev')
commit = metadata.get('commit', 'no-commit')
compile_time = metadata.get('compile_time', 'dev-mode')
indev = not getattr(sys, 'frozen', False)
