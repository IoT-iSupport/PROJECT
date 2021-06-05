import json
import requests
from myMQTT import *
from datetime import datetime
import sys

class LightShift():
	def __init__(self,CATALOG_URL,bT,clientID):
		self.dict=[] 
		self.CATALOG_URL = CATALOG_URL
		self.baseTopic = bT
		self.clientID=clientID

		#initialisation for broker and port
		self.broker=''
		self.port=0

	def start(self):
		self.client.start()
	
	def controlStrategy(self): #it checks if it's time to switch on/off the lights
		for patient in self.dict:
			topic=f'{self.baseTopic}{patient["patientID"]}/actuators/Light'
			times=patient["time"].split('-') # structure of LightsSchedule "7:00-7:30"
			now=datetime.today().time() #current time
			t1=datetime.strptime(times[0],"%H:%M").time() #time to switch on the lights 
			t2=datetime.strptime(times[1],"%H:%M").time() #time to switch off the lights 
			
			if t1<=now<=t2: # if it's time to switch on the lights... 
				if patient["status"]==0: # if lights are switched off, an actuation command is sent to switched lights of this patient on (nothing is done if lights are already switched on)
					patient["status"]=1
					msg={'patientID':patient["patientID"], 
						'bn':'ligth_'+str(patient["patientID"]),
						'e':
							[
								{'n':'Light','value':1, 'timestamp':time.time(),'unit':'Bool'},
								]
						}
					self.client.myPublish(topic,msg)
			else: # if it's time to switch off the Lights... 
				if patient["status"]==1: #... and Lights are switched on
					patient["status"]=0
					msg={'patientID':patient["patientID"], 
						'bn':'light_'+str(patient["patientID"]),
						'e':
							[
								{'n':'Light','value':0, 'timestamp':time.time(),'unit':'Bool'},
								]
						}
					self.client.myPublish(topic,msg) #an actuation command is sent to switch lights of this patient off

	def CatalogCommunication(self):
		r=requests.get(self.CATALOG_URL+f'/broker') #retrieve broker/port 
		if self.broker and self.port: #if broker and port already exist...
			if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #check if the broker is changed...
				self.broker = r.json()["IPaddress"] #... update broker and port
				self.port = r.json()["port"]
				self.client.stop() #stop the previous client and 
				self.client=MyMQTT(self.clientID,self.broker,self.port) #create and start new client
				self.start()	
		else: #create and start new client
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client=MyMQTT(self.clientID,self.broker,self.port)
			self.start()
		
		#retrieve patient ID and LightsSchedule
		r=requests.get(CATALOG_URL+f'/patients') 
		body2=r.json()
		patient_ID_list=[ID["patientID"] for ID in self.dict] #list of patient ID already retrieved and present in self.dict
		for item in body2:
			if not item["patientID"] in patient_ID_list: #if the patient ID is not present in self.dict, it's added
				new_patient={"patientID":item["patientID"], "time":item["LightsSchedule"],'status':0} #light status: 0 off, status: 1 on
				self.dict.append(new_patient)
			else: #if it is present, "LightsSchedule" is updated
				for patient in self.dict:
					if patient["patientID"]==item["patientID"]:
						patient["time"]=item["LightsSchedule"]
		
if __name__=="__main__":
	# sys.argv[1] is the Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"]
	clientID=conf["LightShift"]["clientID"] 
	fp.close()

	LS=LightShift(CATALOG_URL,bT,clientID)	
	while True:
		#every 60s broker/port and patient "LightsSchedule" are  retrieved and control strategy is performed to check if it's time to switch on/off lights
		LS.CatalogCommunication()
		LS.controlStrategy()
		time.sleep(60)
