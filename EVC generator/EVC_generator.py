import cwt,base45,zlib,json
import time,datetime, unidecode,os
import tkinter
from pathlib import Path
from rdflib import *
from base45 import b45decode,b45encode
from cwt import Claims,COSEKey

default={
        'nam': {
            'fn': 'KAAG', 'gn': 'Francois',
            'fnt': 'KAAG', 'gnt': 'François'
            },
        'dob': '1963-07-19',
    "v": [{
            "reg": "FRA", "rep":3,"i": 3141,
            "dt": "1964-02-11", 
            "mp": "VAC0138","vn": "Diphtheria-Tetanus-Pertussis-Polio vaccine, unspecified"
        }, {
            "reg": "FRA", "rep": 3,"i": 5926,
            "dt": "1965-04-05",
            "mp": "VAC0138","vn": "Diphtheria-Tetanus-Pertussis-Polio vaccine, unspecified"
        }, {
            "reg": "FRA","rep": 3,"i": 535,
            "dt": "1971-06-14",
            "mp": "VAC0134","vn": "BCG vaccine, unspecified"
        }, {
            "reg": "FRA","rep": 3,"i": 8979,
            "dt": "1972-10-12",
            "mp": "VAC0063","vn": "TETRACOQ"
        } ]}

# Données de signature
priv_pem="-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIMsO/7yefxo+gG7Gnpz4UG4t3Fn7l/+tqJmM1dL/Xqtv\n-----END PRIVATE KEY-----"
pub_pem="-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA4slb4ugEYVeVYaGZ8OXAz8uXZiNd5yno0h3JZBhCLlM=\n-----END PUBLIC KEY-----"
vkid='33'
priv_key=COSEKey.from_pem(priv_pem,kid=vkid)
pub_key=COSEKey.from_pem(pub_pem,kid=vkid)

def doClear():
    source.delete('1.0',tkinter.END)

def doReload():
    source.delete('1.0',tkinter.END)
    source.insert('1.0',json.dumps(default,ensure_ascii=False))

def doShrink():
    ejson = source.get('1.0',tkinter.END)
    edata = json.loads(ejson)
    today= int(datetime.datetime.timestamp(datetime.datetime.now()))
    validity=int(datetime.datetime.timestamp(datetime.datetime.now() + datetime.timedelta(days=3650)))
    sdata = {
        "iss":"SYA",
        "exp": validity,
        "iat":today,
        "hcert":{
                "ver":"1.0.0",
                "nam":{
                    "fnt": edata['nam']['fnt'],
                    "gnt": edata['nam']['gnt']
                    },
                "dob":edata['dob'],
                "v":[]}
        }
  
    dob = datetime.datetime.strptime(edata['dob'],"%Y-%m-%d")
    
    for vac in edata['v']:
        age = (datetime.datetime.strptime(vac["dt"],"%Y-%m-%d") - dob).days
        vdata = {"reg": vac["reg"],"rep": vac["rep"], "i": vac["i"] ,"a": age,"mp": int(vac["mp"][3:])}
        sdata['hcert']['v'].append(vdata)

    shrinked.delete('1.0',tkinter.END)  
    shrinked.insert('1.0',json.dumps(sdata,ensure_ascii=False))
    result.delete('1.0',tkinter.END)

def doExpand():
    sjson=shrinked.get("1.0",tkinter.END)
    sdata = json.loads(sjson)
    edata = {
        "nam": {
            "fn": unidecode.unidecode(sdata["hcert"]["nam"]["fnt"]),
            "gn": unidecode.unidecode(sdata["hcert"]["nam"]["gnt"]),
            "fnt": sdata["hcert"]["nam"]["fnt"],
            "gnt": sdata["hcert"]["nam"]["gnt"]
            },
        "dob": sdata["hcert"]["dob"],
        "v": []}

    dob = datetime.datetime.strptime(edata['dob'],"%Y-%m-%d")

    for vac in sdata["hcert"]["v"]:
        dt = (dob+datetime.timedelta(vac["a"])).strftime("%Y-%m-%d")
        code = "VAC"+str(vac["mp"]).zfill(4)
        concept = URIRef("http://ivci.org/NUVA#"+code)
        label = g.value(concept,RDFS.label)
        vdata = {"reg": vac["reg"],"rep": vac["rep"], "i": vac["i"], "dt": dt,"mp": code, "vn": label}
        edata["v"].append(vdata)

    source.delete('1.0',tkinter.END)
    source.insert('1.0',json.dumps(edata,ensure_ascii=False))

def doPack():  
    sjson = shrinked.get('1.0',tkinter.END)
    sdata = json.loads(sjson)
    cose = cwt.encode(sdata,priv_key)
    compressed = zlib.compress(cose)
    encoded = b45encode(compressed)

    result.delete('1.0',tkinter.END)
    result.insert('1.0',encoded)
    shrinked.delete('1.0',tkinter.END)

def doUnpack():
    sresult=result.get('1.0',tkinter.END)
    compressed = b45decode(sresult)
    cose=zlib.decompress(compressed)
    decoded=cwt.decode(cose,pub_key)
    claims=Claims.new(decoded)

    sdata={
        'iss': claims.iss,
        'exp': claims.exp,
        'iat': claims.iat,
        'hcert': claims.hcert
        }
    shrinked.delete('1.0',tkinter.END)
    shrinked.insert('1.0',json.dumps(sdata,ensure_ascii=False))
    source.delete('1.0',tkinter.END)

# Retrieve NUVA (fix path according to environment)
print ("Loading NUVA, please wait ...")
g = Graph()
g.parse(str(Path.home())+"/Documents/NUVA/nuva_core.ttl")

#Build window and fields

window=tkinter.Tk()

frame1 = tkinter.Frame()
label1=tkinter.Label(frame1,text='  ORIGINAL  ')
source=tkinter.Text(width=100,height=10)
frame2 = tkinter.Frame()
actShrink=tkinter.Button(frame2,text='Shrink V',command=doShrink)
actExpand=tkinter.Button(frame2, text='Expand ^', command=doExpand)
label2=tkinter.Label(frame2,text='  SHRINKED  ')
shrinked=tkinter.Text(width=100,height=10)
frame3 = tkinter.Frame()
actPack=tkinter.Button(frame3,text='Pack V',command=doPack)
actUnpack=tkinter.Button(frame3,text='Unpack ^',command=doUnpack)
label3=tkinter.Label(frame3, text='  RESULT  ')
result=tkinter.Text(width=100,height=10)

frame1.pack()
label1.pack()
source.pack()
frame2.pack()
actShrink.pack(side="left")
actExpand.pack(side="right")
label2.pack()
shrinked.pack()
frame3.pack()
actPack.pack(side="left")
actUnpack.pack(side="right")
label3.pack()
result.pack()

# Initialize and run

doReload()
window.mainloop()
