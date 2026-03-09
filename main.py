import os,time,random,logging,requests,threading
from datetime import datetime,timedelta
from flask import Flask,jsonify
import pytz

logging.basicConfig(level=logging.INFO,format=’%(asctime)s | %(message)s’)
log=logging.getLogger(**name**)
POLYGON_API_KEY=os.environ.get(‘POLYGON_API_KEY’,’’)
ET=pytz.timezone(‘America/New_York’)
PROFIT_TARGET=0.13
STOP_LOSS=0.10
MAX_TRADES=4
PLAN=[
{“m”:1,“goal”:1000,“stop”:-500,“exp”:2500},
{“m”:2,“goal”:1000,“stop”:-500,“exp”:2500},
{“m”:3,“goal”:1500,“stop”:-750,“exp”:3750},
{“m”:4,“goal”:1500,“stop”:-750,“exp”:3750},
{“m”:5,“goal”:2500,“stop”:-1250,“exp”:6000},
{“m”:6,“goal”:2500,“stop”:-1250,“exp”:6000},
{“m”:7,“goal”:4000,“stop”:-2000,“exp”:9000},
{“m”:8,“goal”:4000,“stop”:-2000,“exp”:9000},
{“m”:9,“goal”:6000,“stop”:-3000,“exp”:13000},
{“m”:10,“goal”:6000,“stop”:-3000,“exp”:13000},
{“m”:11,“goal”:8000,“stop”:-4000,“exp”:20000},
{“m”:12,“goal”:8000,“stop”:-4000,“exp”:20000},
]
S={“running”:True,“day”:1,“month”:1,“account”:37500.0,“dpnl”:0.0,“tpnl”:0.0,“trades”:[],“pos”:None,“log”:[],“scans”:0,“status”:“STARTING”,“wins”:0,“stops”:0}

def plan():
return PLAN[min(S[“month”],12)-1]

def lg(msg,lv=“I”):
S[“log”].insert(0,{“t”:datetime.now(ET).strftime(”%H:%M:%S”),“m”:msg,“l”:lv})
S[“log”]=S[“log”][:100]
log.info(msg)

def market_open():
n=datetime.now(ET)
if n.weekday()>=5:
return False
m=n.hour*60+n.minute
return 570<=m<960

def in_window():
n=datetime.now(ET)
if n.weekday()>=5:
return False
m=n.hour*60+n.minute
return (585<=m<690) or (810<=m<930)

def get_bars():
if not POLYGON_API_KEY:
return None
try:
d=datetime.now(ET).strftime(”%Y-%m-%d”)
r=requests.get(f”https://api.polygon.io/v2/aggs/ticker/SPY/range/1/minute/{d}/{d}?adjusted=true&sort=asc&limit=390&apiKey={POLYGON_API_KEY}”,timeout=10)
data=r.json()
return data.get(“results”) if data.get(“resultsCount”,0)>=20 else None
except:
return None

def analyze():
bars=get_bars()
if bars and len(bars)>=20:
c=[b[“c”] for b in bars]
h=[b[“h”] for b in bars]
l=[b[“l”] for b in bars]
spy=c[-1]
tp=sum(((b[“h”]+b[“l”]+b[“c”])/3)*b[“v”] for b in bars)
vol=sum(b[“v”] for b in bars)
vwap=round(tp/vol,2) if vol else spy
k9=2/10
e9=sum(c[:9])/9
for x in c[9:]:
e9=x*k9+e9*(1-k9)
k20=2/21
e20=sum(c[:20])/20
for x in c[20:]:
e20=x*k20+e20*(1-k20)
e9=round(e9,2)
e20=round(e20,2)
pl=l[-2] if len(l)>1 else spy-0.5
ph=h[-2] if len(h)>1 else spy+0.5
ig=c[-1]>c[-2] if len(c)>1 else True
src=“LIVE”
else:
base=S.get(”_spy”,560.0)
spy=round(base+random.uniform(-0.8,0.8),2)
S[”_spy”]=spy
vwap=round(spy+random.uniform(-1,1),2)
e9=round(spy+random.uniform(-0.8,0.5),2)
e20=round(spy+random.uniform(-1.5,0.2),2)
pl=spy-random.uniform(0.2,1)
ph=spy+random.uniform(0.2,1)
ig=random.random()>0.48
src=“SIM”
av=spy>vwap
be=e9>e20
bea=e9<e20
bull=av and be and (pl<=vwap or pl<=e9) and ig
bear=not av and bea and (ph>=vwap or ph>=e9) and not ig
return {“spy”:spy,“vwap”:vwap,“e9”:e9,“e20”:e20,“bull”:bull,“bear”:bear,“src”:src}

def enter(direction,a):
p=plan()
spy=a[“spy”]
strike=(round(spy)+1) if direction==“CALL” else (round(spy)-1)
entry=max(0.40,round(2.8-abs(spy-strike)*0.9+random.uniform(-0.2,0.3),2))
ct=max(1,int(p[“exp”]/(entry*100)))
tgt=round(entry*(1+PROFIT_TARGET),2)
stp=round(entry*(1-STOP_LOSS),2)
S[“pos”]={“dir”:direction,“strike”:strike,“entry”:entry,“ct”:ct,“tgt”:tgt,“stp”:stp,“cur”:entry,“at”:datetime.now(ET).strftime(”%H:%M:%S”)}
S[“status”]=“IN TRADE “+direction+” $”+str(strike)
lg(“ENTERED “+direction+” $”+str(strike)+” entry=$”+str(entry)+” x”+str(ct)+” tgt=$”+str(tgt)+” stp=$”+str(stp),“T”)

def check():
pos=S[“pos”]
if not pos:
return
cur=round(max(0.05,pos[“cur”]*(1+random.uniform(-0.06,0.09))),2)
pos[“cur”]=cur
pct=(cur-pos[“entry”])/pos[“entry”]
pnl=round((cur-pos[“entry”])*pos[“ct”]*100,2)
lg(pos[“dir”]+” $”+str(pos[“strike”])+” cur=$”+str(cur)+” pnl=”+str(round(pct*100,1))+”%”)
if cur>=pos[“tgt”]:
close(cur,“TARGET”,pnl,pct)
elif cur<=pos[“stp”]:
close(cur,“STOP”,pnl,pct)

def close(ep,reason,pnl,pct):
pos=S[“pos”]
win=pnl>0
S[“trades”].append({**pos,“ep”:ep,“pnl”:pnl,“pct”:round(pct*100,2),“result”:“WIN” if win else “STOP”})
S[“pos”]=None
S[“dpnl”]=round(S[“dpnl”]+pnl,2)
S[“tpnl”]=round(S[“tpnl”]+pnl,2)
S[“account”]=round(S[“account”]+pnl,2)
if win:
S[“wins”]+=1
else:
S[“stops”]+=1
lg((“WIN” if win else “STOP”)+” “+reason+” $”+str(ep)+” “+str(round(pct*100,1))+”% $”+str(pnl)+” daily=$”+str(S[“dpnl”]),“T”)
S[“status”]=“SCANNING”

def bot():
lg(“SPY Bot started”,“S”)
last=datetime.now(ET).date()
while S[“running”]:
now=datetime.now(ET)
today=now.date()
p=plan()
if today!=last:
lg(“New day “+str(S[“day”])+” goal=$”+str(p[“goal”])+” acct=$”+str(S[“account”]),“S”)
S[“dpnl”]=0.0
S[“pos”]=None
S[“day”]+=1
last=today
if S[“pos”]:
check()
time.sleep(30)
continue
if S[“dpnl”]<=p[“stop”]:
S[“status”]=“HALTED-LOSS”
lg(“Loss limit hit”,“W”)
time.sleep(300)
continue
if S[“dpnl”]>=p[“goal”]:
S[“status”]=“HALTED-GOAL”
lg(“Goal reached $”+str(S[“dpnl”]),“S”)
time.sleep(300)
continue
if len(S[“trades”])>=MAX_TRADES:
S[“status”]=“HALTED-MAX”
time.sleep(300)
continue
if not market_open():
S[“status”]=“CLOSED”
lg(“Market closed”)
time.sleep(300)
continue
if not in_window():
S[“status”]=“OUTSIDE WINDOW”
lg(“Outside window”)
time.sleep(60)
continue
S[“scans”]+=1
S[“status”]=“SCANNING”
a=analyze()
lg(“Scan #”+str(S[“scans”])+” [”+a[“src”]+”] SPY=$”+str(a[“spy”])+” VWAP=$”+str(a[“vwap”])+” 9EMA=$”+str(a[“e9”])+” 20EMA=$”+str(a[“e20”]))
if a[“bull”]:
lg(“BULL SETUP”,“T”)
enter(“CALL”,a)
elif a[“bear”]:
lg(“BEAR SETUP”,“T”)
enter(“PUT”,a)
else:
lg(“No setup”)
S[“status”]=“SCANNING-NO SETUP”
time.sleep(60)

app=Flask(**name**)

@app.route(’/’)
def home():
p=plan()
rows=””
for t in reversed(S[“trades”]):
color=”#00ff00” if t[“pnl”]>=0 else “#ff0000”
dcolor=”#00ff00” if t[“dir”]==“CALL” else “#ff0000”
rows+=”<tr><td>”+t[“at”]+”</td><td style='color:"+dcolor+"'>”+t[“dir”]+”</td><td>$”+str(t[“strike”])+”</td><td>$”+str(t[“entry”])+”</td><td>$”+str(t.get(“ep”,“open”))+”</td><td style='color:"+color+"'>$”+str(t[“pnl”])+”</td><td>”+t[“result”]+”</td></tr>”
logs=””
for e in S[“log”][:50]:
if e[“l”]==“T”:
color=”#00ff00”
elif e[“l”]==“W”:
color=”#ff0000”
elif e[“l”]==“S”:
color=”#0088ff”
else:
color=”#aaaaaa”
logs+=”<div style='padding:4px 0;border-bottom:1px solid #111;font-family:monospace;font-size:12px;color:"+color+"'><span style='color:#555;margin-right:8px'>”+e[“t”]+”</span>”+e[“m”]+”</div>”
pos_html=””
if S[“pos”]:
pos_html=”<div style='background:#001a00;border:1px solid #00ff00;padding:10px;margin:10px 0;color:#00ff00;font-family:monospace'>OPEN: “+S[“pos”][“dir”]+” $”+str(S[“pos”][“strike”])+” entry=$”+str(S[“pos”][“entry”])+” now=$”+str(S[“pos”][“cur”])+” tgt=$”+str(S[“pos”][“tgt”])+” stp=$”+str(S[“pos”][“stp”])+”</div>”
total=S[“wins”]+S[“stops”]
wr=round(S[“wins”]/total*100,1) if total>0 else 0
dpnl_color=”#00ff00” if S[“dpnl”]>=0 else “#ff0000”
tpnl_color=”#00ff00” if S[“tpnl”]>=0 else “#ff0000”
return “””<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SPY Bot</title><meta http-equiv="refresh" content="15"><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#03050a;color:#c5d5ee;font-family:sans-serif;padding:16px}h1{font-size:1.8rem;color:#fff;margin-bottom:4px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:16px 0}.card{background:#0c1220;border:1px solid #151f35;padding:14px;border-radius:4px}.lbl{font-size:11px;color:#3a5070;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}.val{font-size:1.6rem;font-weight:bold}.box{background:#0c1220;border:1px solid #151f35;padding:14px;border-radius:4px;margin-bottom:12px}table{width:100%;border-collapse:collapse;font-family:monospace;font-size:12px}th{color:#3a5070;font-size:11px;padding:6px;border-bottom:1px solid #151f35;text-align:left}td{padding:6px;border-bottom:1px solid #0a1020}</style></head><body>””” +   
“<h1>SPY<span style='color:#00ff00'>BOT</span></h1>” +   
“<div style='font-size:11px;color:#3a5070;margin-bottom:12px'>LIVE SIM - DAY “+str(S[“day”])+” - “+S[“status”]+”</div>” +   
pos_html +   
“<div class='grid'>” +   
“<div class='card'><div class='lbl'>Daily P&L</div><div class='val' style='color:"+dpnl_color+"'>$”+str(S[“dpnl”])+”</div><div style='font-size:11px;color:#3a5070;margin-top:4px'>Goal $”+str(p[“goal”])+” Stop -$”+str(abs(p[“stop”]))+”</div></div>” +   
“<div class='card'><div class='lbl'>Account</div><div class='val' style='color:#fff'>$”+str(int(S[“account”]))+”</div><div style='font-size:11px;color:#3a5070;margin-top:4px'>Started $37,500</div></div>” +   
“<div class='card'><div class='lbl'>Total P&L</div><div class='val' style='color:"+tpnl_color+"'>$”+str(S[“tpnl”])+”</div><div style='font-size:11px;color:#3a5070;margin-top:4px'>”+str(total)+” trades - “+str(wr)+”% wins</div></div>” +   
“<div class='card'><div class='lbl'>W / L</div><div class='val'><span style='color:#00ff00'>”+str(S[“wins”])+“W</span> - <span style='color:#ff0000'>”+str(S[“stops”])+“L</span></div></div>” +   
“</div>” +   
“<div class='box'><div style='font-size:13px;font-weight:bold;color:#fff;margin-bottom:10px'>LIVE LOG</div>”+logs+”</div>” +   
“<div class='box'><div style='font-size:13px;font-weight:bold;color:#fff;margin-bottom:10px'>TRADES</div><table><thead><tr><th>Time</th><th>Dir</th><th>Strike</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Result</th></tr></thead><tbody>”+(rows or “<tr><td colspan='7' style='text-align:center;color:#3a5070;padding:16px'>No trades yet</td></tr>”)+”</tbody></table></div></body></html>”

@app.route(’/api/state’)
def state():
return jsonify(S)

if **name**==’**main**’:
threading.Thread(target=bot,daemon=True).start()
port=int(os.environ.get(‘PORT’,5000))
lg(“Dashboard on port “+str(port),“S”)
app.run(host=‘0.0.0.0’,port=port,debug=False)
