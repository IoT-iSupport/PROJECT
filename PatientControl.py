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

clientID = 'PatientControl'
# endTopic = ['HeartRate','Accelerometer']

class PatientControl():
	def __init__(self,CATALOG_URL,baseTopic,endTopic):
		self.endTopic = endTopic
		self.dict=[] # the windows are filled until the 10*60/60s = 10 samp
		self.WriteBaseUrl="https://api.thingspeak.com/update?api_key="
		self.jump=0
		self.CATALOG_URL = CATALOG_URL
		self.baseTopic = baseTopic

	def start(self):
		self.client.start()
		for t in self.endTopic:
			topic=f'{self.baseTopic}+/sensors/'+t
			self.client.mySubscribe(topic)

	def notify(self,topic,payload):
		payload=json.loads(payload)
		topic=topic.split('/')
		id=int(topic[1]) 

		for patient in self.dict:
			if int(patient["patientID"])==id:
				if topic[3]=='HeartRate':
					if len(patient["windowHR"])==len(patient["windowACC"]):
						patient["windowHR"].append(payload["e"][0]["value"])
					else:
						patient["windowHR"].pop()
						patient["windowHR"].append(payload["e"][0]["value"])
				elif topic[3]=='Accelerometer':
					if len(patient["windowHR"])-1==len(patient["windowACC"]):
						#if it has recieved a HR measurement first
						patient["windowACC"].append(payload["e"][0]["value"])
					else:
						print(f'lenHR: {len(patient["windowHR"])}, \n lenACC: {len(patient["windowACC"])}')
						#if not, the couple HR-ACC of the same time is not recorded. So Discard the HR measure
						patient["windowHR"].pop()
				print(f'Patient: {patient["patientID"]}, windows: {patient["windowHR"]},{patient["windowACC"]}\n')

	def controlStrategy(self):
		#removing of the first Measure and windows control
		for patient in self.dict:
			l=len(patient["windowHR"])
			if l>=10 or len(patient["windowACC"])>=10: 
				if not 'lastHR' in patient: #first window observed: no comparing for the first observation
					patient['lastHR']=median(patient["windowHR"])
					patient['lastACC']=median(patient["windowACC"])
				else:
					while patient["windowHR"]!=10:
						patient["windowHR"].pop(0) 
					while patient["windowACC"]!=10:
						patient["windowACC"].pop(0) 
					print(len(patient["windowACC"]))
					if median(patient["windowHR"]) > 1.5*patient['lastHR']:
						print('Condizione HR fatta')
						if median(patient["windowACC"]) < 1.2*patient['lastACC']:
							print('Condizione ACC fatta: PANIK ATTAAAAAAAACK')
							url=f'{self.WriteBaseUrl}{patient["apikey"]}&field4=1' #for collecting panik attack event
							r=requests.get(url) #ThingSpeak request for panik attack event
							print(url)
							msg={"patientID":patient["patientID"],"alertStatus":1}
							topicTelegram=self.baseTopic+str(patient["patientID"])+'/telegram'
							self.client.myPublish(topicTelegram,msg) #message to the care giver and the doctor of the patient for the panik attack event
							#publish per il Device Connector per la musica (?)

	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(self.CATALOG_URL+f'/broker') 
		body=r.json()
		broker=body["IPaddress"]
		port=body["port"]
		r=requests.get(self.CATALOG_URL+f'/token') 
		body=r.json()
		self.token=body
		#patients information
		r=requests.get(self.CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		for item in body2:
			new_patient={"patientID":item["patientID"], "apikey": item["apikey"][0],"windowHR":[],"windowACC":[]}
			self.dict.append(new_patient)
		self.client=MyMQTT(clientID,broker,port,self) 

if __name__=="__main__":
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	endTopic = conf["PatientControl"]["endTopic"]
	close(fp)
	
	PC=PatientControl(CATALOG_URL,bT,endTopic)
	PC.CatalogCommunication()
	PC.start()
	tic=time.time()
	while True:
		if time.time()-tic>=120:
			PC.controlStrategy()
			tic=time.time()

	