import sqlite3,secrets,hashlib,hmac,json,time,re
class Auth:
 def __init__(self,path):
  self.path=path
  with self.db() as d:d.executescript('CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE,name TEXT,salt TEXT,password TEXT,state TEXT);CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user TEXT,expires REAL);')
 def db(self):return sqlite3.connect(self.path,timeout=10)
 def user(self,token):
  with self.db() as d:
   r=d.execute('SELECT u.id,u.email,u.name,u.state FROM users u JOIN sessions s ON s.user=u.id WHERE s.token=? AND s.expires>?',(token,time.time())).fetchone()
   return {'user':{'id':r[0],'email':r[1],'name':r[2]},'state':json.loads(r[3]) if r[3] else None} if r else {'user':None,'state':None}
 def login(self,p,signup,guest,store):
  email=str(p.get('email','')).strip().lower();password=p.get('password','');name=str(p.get('name','')).strip()
  if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or not isinstance(password,str) or not 8<=len(password)<=128:raise ValueError('이메일은 name@example.com 형식으로, 비밀번호는 8~128자로 입력해주세요.')
  with self.db() as d:
   if signup:
    if not 1<=len(name)<=24:raise ValueError('닉네임은 1~24자입니다.')
    uid=secrets.token_hex(24);salt=secrets.token_hex(16);hashed=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
    try:d.execute('INSERT INTO users VALUES(?,?,?,?,?,NULL)',(uid,email,name,salt,hashed))
    except sqlite3.IntegrityError:raise ValueError('이미 가입된 이메일입니다.')
    # Same database transaction transfers guest data to the newly created account.
    for table in ['accounts','activity','surveys','profiles']:d.execute(f'UPDATE {table} SET owner=? WHERE owner=?',(uid,guest))
    d.execute('UPDATE accounts SET nickname=? WHERE owner=?',(name,uid))
   else:
    row=d.execute('SELECT id,salt,password FROM users WHERE email=?',(email,)).fetchone()
    if not row or not hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),row[1].encode(),600000).hex(),row[2]):raise ValueError('이메일 또는 비밀번호가 올바르지 않습니다.')
    uid=row[0]
   token=secrets.token_urlsafe(32);d.execute('INSERT INTO sessions VALUES(?,?,?)',(token,uid,time.time()+30*86400))
  return token,self.user(token)
 def logout(self,token):
  with self.db() as d:d.execute('DELETE FROM sessions WHERE token=?',(token,))
 def state(self,token,state):
  u=self.user(token)['user']
  if not u:raise ValueError('로그인이 필요합니다.')
  if not isinstance(state,dict):raise ValueError('저장 형식 오류')
  with self.db() as d:d.execute('UPDATE users SET state=? WHERE id=?',(json.dumps(state,ensure_ascii=False),u['id']))
