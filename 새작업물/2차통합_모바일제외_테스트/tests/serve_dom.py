import sys,json,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from quick_survey import cloud
from quick_survey.local_web import create_server
for p in (root/'cache').glob('*.json'):
 row=json.loads(p.read_text());cloud.ROWS[row['data']['appid']]=row
cloud.STATE.update(done=len(cloud.ROWS),total=len(cloud.ROWS))
with tempfile.TemporaryDirectory() as directory:
 server=create_server(directory=directory);print(server.server_port,flush=True);server.serve_forever()
