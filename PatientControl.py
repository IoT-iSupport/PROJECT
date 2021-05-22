# is a control strategy for monitoring data from the sensors that interact with the patient 
# (heart rate sensor, accelerometer), communicating via MQTT protocol with the Device Connector
# (information about the Broker are retrived through REST Web Service from the Catalog). 
# It integrates a strategy that identifies abnormal values from the heart rate (H.R.) sensor and accelerometer: 
# if an increase in heart rate is detected with no corresponding change in the patient's activity state a panic attack is detected.
#  For example, if in a 10-minute observation window an increase in heart rate of 50% is detected and accelerometer activity
#  in the same observation window is increased less than 20%, a panic attack is detected. 
# In this case the Patient Control publishes via MQTT to:
# •	the ThingSpeak the event and the timestamp;
# •	the telegramBot the event and the timestamp;
# •	the Device Connector a actuation command for activating the music player. - da rivalutare
import json
import requests
from myMQTT import *
from statistics import median
import sys

class PatientControl():
	def __init__(self,CATALOG_URL,baseTopic,clientID):
		#self.endTopic = endTopic
		self.dict=[] # the windows are filled until the 10*60/60s = 10 samp
		self.WriteBaseUrl="https://api.thingspeak.com/update?api_key="
		self.ReadBaseUrl= "https://api.thingspeak.com/channels/"
		self.jump=0
		self.CATALOG_URL = CATALOG_URL
		self.baseTopic = baseTopic
		self.clientID=clientID
		self.broker=''
		self.token=0

	def start(self):
		self.client.start()
		# for t in self.endTopic:
		# 	topic=f'{self.baseTopic}+/sensors/'+t
		# 	self.client.mySubscribe(topic)

	# def notify(self,topic,payload):
	# 	payload=json.loads(payload)
	# 	topic=topic.split('/')
	# 	id=int(topic[1]) 

	# 	for patient in self.dict:
	# 		if int(patient["patientID"])==id:
	# 			if topic[3]=='HeartRate':
	# 				if len(patient["windowHR"])==len(patient["windowACC"]):
	# 					patient["windowHR"].append(payload["e"][0]["value"])
	# 				else:
	# 					patient["windowHR"].pop()
	# 					patient["windowHR"].append(payload["e"][0]["value"])
	# 			elif topic[3]=='Accelerometer':
	# 				if len(patient["windowHR"])-1==len(patient["windowACC"]):
	# 					#if it has recieved a HR measurement first
	# 					patient["windowACC"].append(payload["e"][0]["value"])
	# 				else:
	# 					print(f'lenHR: {len(patient["windowHR"])}, \n lenACC: {len(patient["windowACC"])}')
	# 					#if not, the couple HR-ACC of the same time is not recorded. So Discard the HR measure
	# 					patient["windowHR"].pop()
	# 			print(f'Patient: {patient["patientID"]}, windows: {patient["windowHR"]},{patient["windowACC"]}\n')

	def controlStrategy(self):
		#removing of the first Measure and windows control
		for patient in self.dict:
			url=f'{self.ReadBaseUrl}{patient["channel"]}/fields/1.json?minutes=10'
			r=requests.get(url) #retrive 10 minutes Accelerometer data
			body=r.json()
			#print(body)
			
			url=f'{self.ReadBaseUrl}{patient["channel"]}/fields/2.json?minutes=10'
			r=requests.get(url) #retrive 10 minutes HR data
			body2=r.json()
			# print(body2)

			if body!=-1 and body2!=-1: #data retived correctly
				patient["windowHR"] = [float(item["field1"]) for item in body["feeds"] if item["field1"]!=None ]
				patient["windowACC"] = [float(item["field2"]) for item in body2["feeds"] if item["field2"]!=None ]
				# for item in body["feeds"]:
				# 	patient["windowHR"].append(item["field1"])
				# for item in body2["feeds"]:
				# 	patient["windowACC"].append(item["field2"])
				
				if patient["windowHR"] != [] and patient["windowACC"] != []:

					if not 'lastHR' in patient: #first window observed: no comparing for the first observation
						patient['lastHR']=median(patient["windowHR"])
						patient['lastACC']=median(patient["windowACC"])
						
					
					if median(patient["windowHR"]) > 1.5*patient['lastHR']:
						print('Condizione HR fatta')
						if not abs(median(patient["windowACC"])) > 2*abs(patient['lastACC']):
							print('Condizione ACC fatta: EMERGENCY ALERT!')
							# print('Panik attack DETECTED')
							url=f'{self.WriteBaseUrl}{patient["apikeyWrite"]}&field4=1' #for collecting panik attack event
							print(url)
							msg={"patientID":patient["patientID"],"alertStatus":1}
							topicTelegram=self.baseTopic+str(patient["patientID"])+'/telegram'
	
							self.client.myPublish(topicTelegram,msg)
							sleep_msg ={'msg':'sleep'}
							topicTS = self.baseTopic+str(patient["patientID"])+'/PA'
							self.client.myPublish(topicTS,sleep_msg)
							time.sleep(15)
							r=requests.get(url) #ThingSpeak request for panik attack event
							
					
					patient['lastHR']=median(patient["windowHR"])
					patient['lastACC']=median(patient["windowACC"])
		
					print(f'HR current window:\n {patient["windowHR"]}')
					print(f"HR current median: {patient['lastHR']}")
					
					print(f'Acceleration current window:\n {patient["windowACC"]}')
					print(f"Acceleration current median: {patient['lastACC']}")
					
	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(self.CATALOG_URL+f'/broker') 
		if self.broker and self.port:
			
			if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #if the broker is changed
				self.broker = r.json()["IPaddress"]
				self.port = r.json()["port"]
				self.client.stop()
				self.client=MyMQTT(self.clientID,self.broker,self.port)
				self.start()	
		else:
		
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client=MyMQTT(self.clientID,self.broker,self.port)
			self.start()

		r=requests.get(self.CATALOG_URL+f'/token')
		if self.token:
			if not self.token== r.json():
				self.token=r.json()
		else:
			self.token=r.json()

		#patients information
		r=requests.get(self.CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		patient_ID_list=[ID["patientID"] for ID in self.dict]
		for item in body2:
			if not item["patientID"] in patient_ID_list:
				new_patient={"patientID":item["patientID"], "channel":item["channel"], "apikeyWrite": item["apikey"][0],"apikeyRead": item["apikey"][1],"windowHR":[],"windowACC":[]}
				self.dict.append(new_patient)
			else:
				for patient in self.dict:
					if patient["patientID"]==item["patientID"]:
						patient["apikeyWrite"]=item["apikey"][0] #... update apikey and channel
						patient["apikeyRead"]=item["apikey"][1]
						patient["channel"]=item["channel"]	
			

if __name__=="__main__":
	fp = open(sys.argv[1])
	#fp='Configuration_file.json'
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	#endTopic = conf["PatientControl"]["endTopic"]
	clientID = conf["PatientControl"]["clientID"]
	print(clientID)
	fp.close()
	
	PC=PatientControl(CATALOG_URL,bT,clientID)
	PC.CatalogCommunication()
	tic=time.time()
	while True:
		if time.time()-tic>=(60*5):
			PC.CatalogCommunication()
			PC.controlStrategy()
			tic=time.time()
	
	
	
