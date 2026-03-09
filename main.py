import os,time,random,logging,requests,threading
from datetime import datetime,timedelta
from flask import Flask,jsonify
import pytz

logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(message)s')
log=logging.getLogger(__name__)
POLYGON_API_KEY=os.environ.get('POLYGON_API_KEY','')
ET=pytz.timezone('America/New_York')
PROFIT_TARGET=0.13
STOP_LOSS=0.10
MAX_TRADES=4
PLAN=[
{"m":1,"goal":1000,"stop":-500,"exp":2500},
{"m":2,"goal":1000,"stop":-500,"exp":2500},
{"m":3,"goal":1500,"stop":-750,"exp":3750},
{"m":4,"goal":1500,"stop":-750,"exp":3750},
{"m":5,"goal":2500,"stop":-1250,"exp":6000},
{"m":6,"goal":2500,"stop":-1250,"exp":6000},
{"m":7,"goal":4000,"stop":-2000,"exp":9000},
{"m":8,"goal":4000,"stop":-2000,"exp":9000},
{"m":9,"goal":6000,"stop":-3000,"exp":13000},
{"m":10,"goal":6000,"stop":-3000,"exp":13000},
{"m":11,"goal":8000,"stop":-4000,"exp":20000},
{"m":12,"goal":8000,"stop":-4000,"exp":20000},
]
S={"running":True,"day":1,"month":1,"account":37500.0,"dpnl":0.0,"tpnl":0.0,"trades":[],"pos":None,"log":[],"scans":0,"status":"STARTING","wins":0,"stops":0}

def plan():return PLAN[min(S["month"],12)-1]
def lg(msg,lv="I"):
    S["log"].insert(0,{"t":datetime.now(ET).strftime("%H:%M:%S"),"m":msg,"l":lv})
    S["log"]=S["log"][:100];log.info(msg)
def market_open():
    n=datetime.now(ET)
    if n.weekday()>=5:return False
    m=n.hour*60+n.minute;return 570<=m<960
def in_window():
    n=datetime.now(ET)
    if n.weekday()>=5:return False
    m=n.hour*60+n.minute;return(585<=m<690)or​​​​​​​​​​​​​​​​

