import json
import time
import cherrypy

class Catalog():
    exposed=True
    def __init__(self,filename):
        self.filename=filename
        fp=open(self.filename)
        body=json.load(fp)
        self.broker=body['broker']
        self.telegramToken=body['token']
        self.devices=body['deviceList']
        self.patients=body['patientList']
        fp.close()
        self.aliveChecker()
    def GET(self,*uri):
        uri=list(uri)
        if not len(uri):
            pass #errore
        else:
            if uri[0]=='broker':
                print(json.dumps(self.broker,indent=4))
                return json.dumps(self.broker,indent=4)
            elif uri[0]=='token':
                return json.dumps(self.telegramToken,indent=4)
            elif uri[0]=='devices':
                return json.dumps(self.devices,indent=4)
            elif uri[0]=='patients':
                output=[]
                for p in self.patients:
                    item={"patientID":p["patientID"],"apikey":[i for i in p["thingspeakInfo"]["apikeys"]],"channel":p["thingspeakInfo"]["channel"],"LightsSchedule":p["LightsSchedule"]}
                    output.append(item)
                print(f'The patient is: {output}')
                return json.dumps(output,indent=4)
            elif uri[0]=='deviceID':
                id=uri[1]
                for item in self.devices:
                    if item['deviceID']==id:
                        return json.dumps(item,indent=4)
                    #controlli 
            elif uri[0]=='patientID':
                id=uri[1]
                for item in self.patients:
                    if item['patientID']==id:
                        return json.dumps(item,indent=4)
                    #controlli 
    def POST(self,*uri):
        uri=list(uri)
        json_body=json.loads(cherrypy.request.body.read())
        json_body["lastUpdate"]=time.time()
        if not len(uri):
            pass #signaling error
        else:
            if uri[0]=='device':
                self.devices.append(json_body)
                self.save()
            elif uri[0]=='patient':
                self.patients.append(json_body)
                self.save()
            else:
                pass#error
            

    def PUT(self,*uri):
        json_body=json.loads(cherrypy.request.body.read()) #hp: le informazioni da modifcare sono nel corpo del PUT in cui ci deve essere sempre l'ID
        uri=list(uri)
        if not len(uri):
            pass #errore
        else:
            if uri[0]=='patient':
                pass
            elif uri[0]=='device':
                for item in self.devices:
                    if item['deviceID']==json_body["deviceID"]:
                        for k in json_body:
                            item[k]=json_body[k]
                        item["lastUpdate"]=time.time()
                self.save()        
        
    def save(self):
        data={"broker":self.broker,
            "token":self.telegramToken,
            "deviceList":self.devices,
            "patientList":self.patients
            }
        fp=open(self.filename,'w')
        json.dump(data,fp,indent=4)
        fp.close()

    def aliveChecker(self):
        if not self.devices==[]:
            ind=[]
            for i,device in list(enumerate(self.devices)):
                print(f'Device: {device["deviceName"]}, i: {i}, diff: {time.time()-device["lastUpdate"]}')
                if time.time()>device["lastUpdate"]+120:
                    print(f'Removed deviceID: {device["deviceID"]}')
                    ind.append(i)
            for i in list(reversed(ind)):
                self.devices.pop(i)        
            self.save()

if __name__ == "__main__":
    c=Catalog("Catalog.json")
    #Standard configuration to serve the url "localhost:8080"
    conf={
        '/':{
                'request.dispatch':cherrypy.dispatch.MethodDispatcher(),
                'tool.session.on':True
        }
    }
    cherrypy.tree.mount(c,'/',conf)
    cherrypy.engine.start()
    while True:
        try:
            while True:
                #checking the connection of the device in the list
                c.aliveChecker()
                time.sleep(60)
        except KeyboardInterrupt:
            raise 
    cherrypy.engine.block()
