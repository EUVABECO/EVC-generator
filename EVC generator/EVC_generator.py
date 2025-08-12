import cwt,base45,zlib,json
import jwcrypto
import qrcode
import time,datetime, unidecode,os
import tkinter
import requests
from pathlib import Path
from rdflib import *
from base45 import b45decode,b45encode
from base64 import b64encode
from cwt import Claims,COSEKey,CWT,load_pem_hcert_dsc
from jwcrypto import jwk
from typing import Any,Union,Dict

class MyCWT(CWT):
    # This is to avoid the optional claims forced by PyCwt: iat,nbf et exp
    def _set_default_value(self, claims: Union[Dict[int, Any], bytes]):
        return

mycwt = MyCWT()

default = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [{"fullUrl": "http://EVC/Patient/this",
            "resource": {
				"text": {"status": "generated", "div":"<div xmlns='http://www.w3.org/1999/xhtml'>Patient John DOË</div>"},
				"id":"this",
                "resourceType": "Patient",
                "name": [{"family": "DOË","given": ["John"] } ],               
                "birthDate": "2017-07-19"
            }},        
       {    "fullUrl": "http://EVC/Immunization/1",
            "resource": {
				"text": {"status":"generated","div":"<div xmlns='http://www.w3.org/1999/xhtml'>REPEVAX administered on 2021-05-05</div>"},
				"id":"1","resourceType": "Immunization",
                "identifier": [{"system": "http://EVC/MasterRecord","value": "FRA/36/2021-05-05/1245"} ],
                "status": "completed",
                "vaccineCode": {
                    "coding": [{"system": "urn:oid:1.3.6.1.4.1.48601.1.1.1","code": "VAC0029","display": "REPEVAX"}] },
                "patient": {"reference": "Patient/this"},
                "occurrenceDateTime": "2021-05-05"				
            }}, 
       {    "fullUrl": "http://EVC/Immunization/2",
            "resource": {
				"text": {"status":"generated","div":"<div  xmlns='http://www.w3.org/1999/xhtml'>QDENGA administered on 2022-03-03</div>"},
				"id":"2","resourceType": "Immunization",
                "identifier": [{"system": "http://EVC/MasterRecord","value": "FRA/36/2022-03-03/127"}],
                "status": "completed",
                "vaccineCode": {
                    "coding": [{"system": "urn:oid:1.3.6.1.4.1.48601.1.1.1","code": "VAC0644","display": "QDENGA"
                        } ] },
                "patient": {"reference": "Patient/this" },
                "occurrenceDateTime": "2022-03-03"				
            }}]}

# Données de signature SYA
jwk_sya = {
            "kty": "EC",
            "crv": "P-256",
            "alg": "ES256",
            "x": "FDMpzOeGjkFpJ1mc9lo0884v/aVafspp7YkZo5TULw8",
            "y": "YPfxp4DYp4O/t6LdayeW6BKNu87509Fo25Uplxo257k",
            "d": "bBOCdlrsU1jxF3M9KBwce9w5iE0EpFoebGfIWLwgbBk",
            "kid": "SYA25A"
          }
myKey =COSEKey.from_jwk(jwk_sya)
keyexp = int(datetime.datetime.strptime("2050-12-31","%Y-%m-%d").timestamp())

# Load public keys
keys = requests.get("https://keys.euvabeco.eu/.well-known/jwks.json")
jwks = json.loads(keys.content)

pubkeys=[]

for key in jwks['keys']:
    kid = key['kid']
    if kid.startswith("0x"):      
        pem= jwk.JWK(kty = key['kty'],crv = key['crv'], x = key['x'],y = key['y']).export_to_pem()
        pubkey=COSEKey.from_pem(pem,kid=bytes.fromhex(kid[2:]))
    else:
        pubkey=COSEKey.from_jwk(key)
    pubkeys.append(pubkey)
        

def doClear():
    source.delete('1.0',tkinter.END)

def doReload():
    source.delete('1.0',tkinter.END)
    source.insert('1.0',json.dumps(default,ensure_ascii=False,indent=2))

def doShrink():
    shrinked.delete('1.0',tkinter.END)
    result.delete('1.0',tkinter.END)

    ejson = source.get('1.0',tkinter.END)
    try:
        edata = json.loads(ejson)
    except:
        shrinked.insert('1.0',"Invalid JSON format")
        return

#    First retrieve patient information
    for entry in edata['entry']:
        resource = entry['resource']
        if resource ['resourceType'] == "Patient":
            fnt = resource['name'][0]['family']
            gnt = resource['name'][0]['given'][0]
            dobstr=resource['birthDate']
            dob = datetime.datetime.strptime(dobstr,"%Y-%m-%d")
            break
# Then vaccines
    v = []
    for entry in edata['entry']:
        resource = entry['resource']
        if resource['resourceType'] == "Immunization":
            age = (datetime.datetime.strptime(resource['occurrenceDateTime'],"%Y-%m-%d") - dob).days
            master=resource['identifier'][0]['value'].split('/')
            vdata = {'reg':master[0],'rep':int(master[1]),'i':int(master[3]),
                     'a':age,
                     'mp':int(resource['vaccineCode']['coding'][0]['code'][3:])}
            v.append(vdata)

    sdata = {"ver":"1.0.0","nam":{"fnt": fnt,"gnt": gnt},"dob":dobstr,"v":v
             }       
    shrinked.insert('1.0',json.dumps(sdata,ensure_ascii=False))

def doExpand():
    source.delete('1.0',tkinter.END)
    result.delete('1.0',tkinter.END)
    image.delete('1.0',tkinter.END)

    sjson=shrinked.get("1.0",tkinter.END)
    try:
        sdata = json.loads(sjson)
    except:
        source.insert('1.0',"Invalid JSON format")
        return

    edata = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [{
		"fullUrl": "http://EVC/Patient/this",
        "resource": {
			"text": {"status": "generated", 
                        "div":"<div xmlns='http://www.w3.org/1999/xhtml'>Patient "
                        +sdata['nam']['gnt']+ " "+sdata['nam']['fnt']+"</div>"},
			"id":"this",
            "resourceType": "Patient",
            "name": [{
                    "family": sdata['nam']['fnt'],
                    "given": [sdata['nam']['gnt']]
                } ],               
            "birthDate": sdata['dob']
            }
        }
    ]
}
       
    dob = datetime.datetime.strptime(sdata['dob'],"%Y-%m-%d")
    index =0

    for vac in sdata ["v"]:
        dt = (dob+datetime.timedelta(vac["a"])).strftime("%Y-%m-%d")
        code = "VAC"+str(vac["mp"]).zfill(4)
        concept = URIRef("http://ivci.org/NUVA/"+code)
        label = g.value(concept,RDFS.label)
        if not label: label="Unknown"
        index += 1

        vdata = {
			"fullUrl": "http://EVC/Immunization/"+str(index),
            "resource": {
				"text": {"status":"generated",
                         "div":"<div  xmlns='http://www.w3.org/1999/xhtml'>"+label+" administered on "+dt+"</div>"},
				"id":str(index),
                "resourceType": "Immunization",
                "identifier": [{
                        "system": "http://EVC/MasterRecord",
                        "value": vac['reg']+"/"+str(vac['rep'])+"/"+dt+"/"+str(vac['i'])
                    }],
                "status": "completed",
                "vaccineCode": {
                    "coding": [{
                            "system": "urn:oid:1.3.6.1.4.1.48601.1.1.1",
                            "code": code,
                            "display": label
                        } ] },
                "patient": {"reference": "Patient/this" },
                "occurrenceDateTime": dt		
            }
        }

        edata['entry'].append(vdata)

    source.insert('1.0',json.dumps(edata,ensure_ascii=False,indent=2))

def doPack():  
    global img
    result.delete('1.0',tkinter.END)
    image.delete('1.0',tkinter.END)

    sjson = shrinked.get('1.0',tkinter.END)
    try:
        sdata = json.loads(sjson)
    except:
        result.insert('1.0',"Invalid JSON format")
        return
    
    today= int(datetime.datetime.timestamp(datetime.datetime.now()))
    topack = {"iss":"SYA","exp":keyexp, "iat":today, "hcert": sdata}

    cose = mycwt.encode(topack,myKey)
    compressed = zlib.compress(cose)
    encoded = b45encode(compressed)

    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data('VC1:'+encoded.decode())
    qrimage = qr.make_image()
    qrimage.save("QRCODE.png")
    img=tkinter.PhotoImage(file='QRCODE.png')
    result.insert('1.0',encoded)
    image.image_create(tkinter.END, image = img)

    shrinked.delete('1.0',tkinter.END)

def doUnpack():
    shrinked.delete('1.0',tkinter.END)
    source.delete('1.0',tkinter.END)

    sresult=result.get('1.0',tkinter.END)
    try:
        compressed = b45decode(sresult)
        cose=zlib.decompress(compressed)
        decoded=cwt.decode(cose,pubkeys)
        claims=Claims.new(decoded)
    except:
        shrinked.insert("1.0","Invalid EVC format")
        return

    shrinked.insert('1.0',json.dumps(claims.hcert,ensure_ascii=False))

# Retrieve NUVA
print ("Loading NUVA, please wait ...")
g = Graph()
g.parse("https://ivci.org/nuva/nuva_core.ttl",format="turtle")

#Build window and fields
window=tkinter.Tk()

frame1 = tkinter.Frame()
label1=tkinter.Label(frame1,text='  FHIR  ')
actClear = tkinter.Button(frame1,text='Clear', command = doClear)
actReload = tkinter.Button(frame1,text='Reload', command = doReload)
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
image=tkinter.Text(width=100,height=50)

frame1.pack()
actClear.pack(side="left")
actReload.pack(side="right")
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
image.pack()

# Initialize and run

doReload()
window.mainloop()
