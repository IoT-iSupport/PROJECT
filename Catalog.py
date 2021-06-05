import json
import time
import cherrypy

class Catalog():
	exposed=True
	def __init__(self,filename):
		#open Catalog.json and create the attributes broker, token, deviceList and patientList
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
			raise cherrypy.HTTPError(400,"Bad Request")
		else:
			#Retrieve IP address and port of the message broker
			if uri[0]=='broker':
				return json.dumps(self.broker,indent=4)
			#Retrieve telegram token
			elif uri[0]=='token':
				return json.dumps(self.telegramToken,indent=4)
			#Retrieve all the registered devices
			elif uri[0]=='devices':
				return json.dumps(self.devices,indent=4)
			#Retrieve all the registered users with their thingspeak apikeys and channel and the light Schedule
			elif uri[0]=='patients':
				output=[]
				for p in self.patients:
					item={"patientID":p["patientID"],"apikey":[i for i in p["thingspeakInfo"]["apikeys"]],"channel":p["thingspeakInfo"]["channel"],"LightsSchedule":p["LightsSchedule"],"telegramIDs":p["telegramIDs"]}
					output.append(item)
				return json.dumps(output,indent=4)
			#It is used by DeviceConnector.py for retriving the registered devices
			elif uri[0]=='deviceID':
				id=uri[1]
				for item in self.devices:
					if item['deviceID']==id:
						return json.dumps(item,indent=4)
			else:
				raise cherrypy.HTTPError(400,"Bad Request")
					
	def POST(self,*uri):
		uri=list(uri)
		json_body = json.loads(cherrypy.request.body.read())
		if not len(uri):
			raise cherrypy.HTTPError(400,"Bad Request")
		else:
			#Add a new device
			if uri[0]=='device':
				json_body["lastUpdate"]=time.time()
				self.devices.append(json_body)
				self.save()
				print(f'\nAdded deviceID: {json_body["deviceID"]}')
			#Add a new user
			elif uri[0]=='patient':
				json_body["lastUpdate"]=time.time()
				self.patients.append(json_body)
				self.save()
			#Add doctor/care giver telegram chatID 
			elif uri[0] == 'chatID':
				for patient in self.patients:
					if int(uri[1])==int(patient["patientID"]):
						patient["telegramIDs"].append(json_body["chatID"])
						self.save()
			else:
				raise cherrypy.HTTPError(404,"Not Found")
			

	def PUT(self,*uri): #hp: information to be updated are in the PUT body with the ID
		json_body=json.loads(cherrypy.request.body.read()) 
		uri=list(uri)
		if not len(uri):
			raise cherrypy.HTTPError(400,"Bad Request")
		else: #Update the information of a patient
			if uri[0]=='patient':
				for item in self.patients:
					if item['patientID']==json_body["patientID"]:
						for k in json_body: # update device information 
							item[k]=json_body[k]
						item["lastUpdate"]=time.time()
			#Update the information of a device
			elif uri[0]=='device':
				for item in self.devices:
					if item['deviceID']==json_body["deviceID"]:
						for k in json_body: # update device information 
							item[k]=json_body[k]
						item["lastUpdate"]=time.time() # always update "lastUpdate"
				self.save()        
			else:
				raise cherrypy.HTTPError(404,"Not Found")
		
	def save(self): #It saves all information in Catalog.json
		data={"broker":self.broker,
			"token":self.telegramToken,
			"deviceList":self.devices,
			"patientList":self.patients
			}
		fp=open(self.filename,'w')
		json.dump(data,fp,indent=4)
		fp.close()

	def aliveChecker(self): #It removes all the devices with “lastUpdate” higher than two minutes.
		if not self.devices==[]:
			ind=[]
			for i,device in list(enumerate(self.devices)):
				#print(f'Device: {device["deviceName"]}, i: {i}, diff: {time.time()-device["lastUpdate"]}')
				if time.time()>device["lastUpdate"]+120:
					print(f'Removed deviceID: {device["deviceID"]}')
					ind.append(i) #append all the indexes of the devices to be removed
			#remove devices starting from the last one and save
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
			#checking the connection of the device in the list
			c.aliveChecker()
			time.sleep(60)
		except KeyboardInterrupt:
			False
	cherrypy.engine.block()
