import json, time, urllib.request, re, datetime, pathlib
P=pathlib.Path(__file__).with_name('index.html'); s=P.read_text(); start=s.index('const D=')+8; end=s.index(';const $=',start); d=json.loads(s[start:end]); known={r[0] for r in d['records']}; new=[]; quiet=0
for page in range(1,101):
    req=urllib.request.Request(f'https://zkillboard.com/api/characterID/454040390/page/{page}/',headers={'User-Agent':'BlueTudorDashboard/1.0 (public character statistics; hourly GitHub Actions)','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as res: rows=json.load(res)
    if not isinstance(rows,list): raise ValueError('Unexpected API response')
    if not rows: break
    added=0
    for r in rows:
        i=r['killmail_id']
        if i not in known: new.append(r); known.add(i); added+=1
    quiet=quiet+1 if not added else 0
    if quiet>=2: break
    time.sleep(2)
else: raise RuntimeError('Page limit reached; manual backfill required')

def bump(m,key,n):
    if key not in m: m[key]=[0]*n
    return m[key]
years=dict(d['years']); months=dict(d['months']); hours=dict(d['hours']); ships=dict(d['ships']); systems=dict(d['systems']); rivals={r[0]:r for r in d['rivals']}; cid=454040390
for r in new:
    v=r['victim']; aa=r['attackers']; own=next((a for a in aa if a.get('character_id')==cid),None); loss=int(v.get('character_id')==cid)
    if not loss and own is None: raise ValueError('Character absent from killmail')
    z=r['zkb']; value=float(z['totalValue']); solo=bool(z.get('solo')); fb=bool(not loss and own.get('final_blow')); t=r['killmail_time']; ship=str((v if loss else own).get('ship_type_id') or 'Unknown'); system=r['solar_system_id']; n=len(aa)
    y=bump(years,t[:4],6); y[loss]+=1; y[2+loss]+=value; y[4]+=int(solo and not loss); y[5]+=int(fb)
    for m,key in [(months,t[:7]),(hours,t[11:13]),(ships,ship),(systems,str(system))]: bump(m,key,2)[loss]+=1
    if not loss:
        d['small'][0]+=int(n<=5); d['small'][1]+=int(n<=10)
    enemies={a['character_id']:a for a in aa if a.get('character_id') and a['character_id']!=cid} if loss else ({v['character_id']:own} if v.get('character_id') else {})
    for enemy,a in enemies.items():
        rr=rivals.setdefault(enemy,[enemy,str(enemy),0,0,0,0,0,0,0,0]); rr[2+loss]+=1; rr[4+loss]+=value; rr[6+loss]+=int(bool(a.get('final_blow'))); rr[8+loss]+=int(solo)
    d['records'].append([r['killmail_id'],t,loss,value,ship,system,n,solo,fb])
for key,m in [('years',years),('months',months),('hours',hours)]: d[key]=sorted(m.items())
for key,m in [('ships',ships),('systems',systems)]: d[key]=sorted(m.items(),key=lambda x:sum(x[1]),reverse=True)
d['rivals']=sorted(rivals.values(),key=lambda x:x[2]+x[3],reverse=True); d['records'].sort(key=lambda x:x[1],reverse=True)
s=s[:start]+json.dumps(d,separators=(',',':'),ensure_ascii=True).replace('<','\\u003c')+s[end:]; now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'); s=re.sub(r'Last successful sync: [^<]*', 'Last successful sync: '+now,s); s=re.sub(r'Historical PvP dossier · Feb 2009 – [^<]*','Historical PvP dossier · Feb 2009 – '+d['records'][0][1][:10],s); s=re.sub(r'Source: supplied blue_tudor_complet.json · [^<]*?killmails\.',f'Source: historical archive and zKillboard API · {len(d["records"]):,} killmails.',s); P.write_text(s); print(f'{len(new)} new records; {len(d["records"])} total')
