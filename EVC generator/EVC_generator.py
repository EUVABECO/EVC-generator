import cwt,base45,zlib,json
import time,datetime, unidecode,os
import tkinter
from pathlib import Path
from rdflib import *
from base45 import b45decode,b45encode
from cwt import Claims,COSEKey

default = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [{
			"fullUrl": "http://EVC/Patient/this",
            "resource": {
				"text": {"status": "generated", "div":"<div xmlns='http://www.w3.org/1999/xhtml'>Patient John DOË</div>"},
				"id":"this",
                "resourceType": "Patient",
                "name": [{
                        "family": "DOË",
                        "given": ["John"]
                    } ],               
                "birthDate": "2017-07-19"
            }
        },        
       {
		   "fullUrl": "http://EVC/Immunization/1",
            "resource": {
				"text": {"status":"generated","div":"<div xmlns='http://www.w3.org/1999/xhtml'>REPEVAX administered on 2021-05-05</div>"},
				"id":"1",
                "resourceType": "Immunization",
                "identifier": [{
                        "system": "http://EVC/MasterRecord",
                        "value": "FRA/36/2021-05-05/1245"
                    } ],
                "status": "completed",
                "vaccineCode": {
                    "coding": [{
                            "system": "urn:oid:1.3.6.1.4.1.48601.1.1.1",
                            "code": "VAC0029",
                            "display": "REPEVAX"
                        }] },
                "patient": {"reference": "Patient/this"},
                "occurrenceDateTime": "2021-05-05"				
            }
        }, 
       {
			"fullUrl": "http://EVC/Immunization/2",
            "resource": {
				"text": {"status":"generated","div":"<div  xmlns='http://www.w3.org/1999/xhtml'>TETRACOQ administered on 2022-03-03</div>"},
				"id":"2",
                "resourceType": "Immunization",
                "identifier": [{
                        "system": "http://EVC/MasterRecord",
                        "value": "FRA/36/2022-03-03/127"
                    }],
                "status": "completed",
                "vaccineCode": {
                    "coding": [{
                            "system": "urn:oid:1.3.6.1.4.1.48601.1.1.1",
                            "code": "VAC0063",
                            "display": "TETRACOQ"
                        } ] },
                "patient": {"reference": "Patient/this" },
                "occurrenceDateTime": "2022-03-03"				
            }
        }
    ]
}

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
        concept = URIRef("http://ivci.org/NUVA#"+code)
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
    result.delete('1.0',tkinter.END)

    sjson = shrinked.get('1.0',tkinter.END)
    try:
        sdata = json.loads(sjson)
    except:
        result.insert('1.0',"Invalid JSON format")
        return
    
    today= int(datetime.datetime.timestamp(datetime.datetime.now()))
    validity=int(datetime.datetime.timestamp(datetime.datetime.now() + datetime.timedelta(days=3650)))

    topack = {"iss":"SYA","exp": validity,"iat":today,"hcert": sdata}

    cose = cwt.encode(topack,priv_key)
    compressed = zlib.compress(cose)
    encoded = b45encode(compressed)

    result.insert('1.0',encoded)
    shrinked.delete('1.0',tkinter.END)

def doUnpack():
    shrinked.delete('1.0',tkinter.END)
    source.delete('1.0',tkinter.END)

    sresult=result.get('1.0',tkinter.END)
    try:
        compressed = b45decode(sresult)
        cose=zlib.decompress(compressed)
        decoded=cwt.decode(cose,pub_key)
        claims=Claims.new(decoded)
    except:
        shrinked.insert("1.0","Invalid EVC format")
        return

    shrinked.insert('1.0',json.dumps(claims.hcert,ensure_ascii=False))

# Retrieve NUVA
print ("Loading NUVA, please wait ...")
g = Graph()
g.parse("nuva_core.ttl")

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

# Initialize and run

doReload()
window.mainloop()
