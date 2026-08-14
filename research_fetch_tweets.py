import json,re,time,html
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor,as_completed
archive_dir=Path(__file__).resolve().parent/'files'/'research_archive'
archive_dir.mkdir(parents=True,exist_ok=True)
rows=json.load((archive_dir/'research_cdx_twitter.json').open())[1:]
ids={re.search(r'/status/(\d+)',r[1]).group(1) for r in rows if re.search(r'/status/(\d+)',r[1])}

def fetch(i):
 u='https://publish.twitter.com/oembed?omit_script=true&dnt=true&url='+quote('https://twitter.com/SanAntonioDSA/status/'+i,safe=':/')
 for n in range(4):
  try:
   with urlopen(Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as x:
    d=json.load(x)
   h=d.get('html','')
   p=re.search(r'<p[^>]*>(.*?)</p>',h,re.S)
   text=html.unescape(re.sub(r'<br\s*/?>','\n',p.group(1) if p else ''))
   text=re.sub(r'<[^>]+>','',text).strip()
   date=''
   m=re.search(r'>([A-Z][a-z]+ \d{1,2}, \d{4})</a>',h)
   if m: date=m.group(1)
   return {'id':i,'url':'https://twitter.com/SanAntonioDSA/status/'+i,'date':date,'text':text}
  except Exception as e:
   if n==3:return {'id':i,'url':'https://twitter.com/SanAntonioDSA/status/'+i,'error':repr(e)}
   time.sleep(1+n)

out=[]
with ThreadPoolExecutor(max_workers=12) as ex:
 futs={ex.submit(fetch,i):i for i in sorted(ids,key=int)}
 for n,f in enumerate(as_completed(futs),1):
  out.append(f.result())
  if n%100==0: print(n,flush=True)
out.sort(key=lambda x:int(x['id']))
json.dump(
 out,
 (archive_dir/'research_tweets.json').open('w'),
 ensure_ascii=False,
 indent=2,
)
print('done',len(out),'errors',sum('error'in x for x in out))
