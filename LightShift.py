import json
import requests
from myMQTT import *
from datetime import datetime
import sys

clientID='LigthShiftMS'

class LigthShift():
	def __init__(self,CATALOG_URL,bT):
		self.dict=[] 
		self.CATALOG_URL = CATALOG_URL
		self.baseTopic = bT
		r=requests.get(self.CATALOG_URL+f'/broker') 
		body=r.json()
		self.broker=body["IPaddress"]
		self.port=body["port"]
		self.client=MyMQTT(clientID,self.broker,self.port,self) 

	def start(self):
		self.client.start()
	
	def controlStrategy(self):
		for patient in self.dict:
			topic=f'{self.baseTopic}{patient["patientID"]}/actuators/Light'
			times=patient["time"].split('-')
			now=datetime.today().time()
			t1=datetime.strptime(times[0],"%H:%M").time()
			t2=datetime.strptime(times[1],"%H:%M").time()
			
			if t1<=now<=t2:
				if patient["status"]==1:
					pass
				else:
					patient["status"]=1
					msg={'patientID':patient["patientID"], 
						'bn':'ligth_'+str(patient["patientID"]),
						'e':
							[
								{'n':'Light','value':1, 'timestamp':time.time(),'unit':'Bool'},
								]
						}
					self.client.myPublish(topic,msg)
					print(topic)
			else:
				if patient["status"]==1:
					patient["status"]=0
					msg={'patientID':patient["patientID"], 
						'bn':'ligth_'+str(patient["patientID"]),
						'e':
							[
								{'n':'Light','value':0, 'timestamp':time.time(),'unit':'Bool'},
								]
						}
					self.client.myPublish(topic,msg) 
					print(topic)

	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(self.CATALOG_URL+f'/broker') 
		if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #if the broker is changed
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client.stop()
			self.client=MyMQTT(clientID,self.broker,self.port,self)
			self.start()
		
		r=requests.get(CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		for item in body2:
			present=0
			for patient in self.dict:
				if item["patientID"]==patient["patientID"]:
					present=1
					patient["time"]=item["LightsSchedule]
			if present==0: #aggiungo il paziente solo se non è già presente
				new_patient={"patientID":item["patientID"], "time":item["LightsSchedule"],'status':0} #status: 0 off, status: 1 on
				self.dict.append(new_patient)
				#print(self.dict)
		

if __name__=="__main__":
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	fp.close()

	LS=LigthShift(CATALOG_URL,bT)
	LS.start()
	
	while True:
		LS.CatalogCommunication()
		LS.controlStrategy()
		time.sleep(60)
