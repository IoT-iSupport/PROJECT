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
		
		#initialisation for broker and port
		self.broker=''
		self.token=0

	def start(self):
		self.client.start()
		
	def controlStrategy(self): #it checks if a panic attack has occurred 
		for patient in self.dict:
			url=f'{self.ReadBaseUrl}{patient["channel"]}/fields/1.json?minutes=10'
			r=requests.get(url) #retrieve 10 minutes Accelerometer data
			body=r.json()
			
			url=f'{self.ReadBaseUrl}{patient["channel"]}/fields/2.json?minutes=10'
			r=requests.get(url) #retrieve 10 minutes HR data
			body2=r.json()

			if body!=-1 and body2!=-1: #data retrieved correctly
				patient["windowHR"] = [float(item["field1"]) for item in body["feeds"] if item["field1"]!=None ] #None are removed
				patient["windowACC"] = [float(item["field2"]) for item in body2["feeds"] if item["field2"]!=None ]
				
				if patient["windowHR"] != [] and patient["windowACC"] != []:

					if not 'lastHR' in patient: #first window observed: no comparing for the first observation
						patient['lastHR']=median(patient["windowHR"])
						patient['lastACC']=median(patient["windowACC"])
						
					
					if median(patient["windowHR"]) > 1.5*patient['lastHR']: #if current HR increases more than 50% of the previous HR
						print('Condizione HR fatta')
						if not abs(median(patient["windowACC"])) > 2*abs(patient['lastACC']): #if current acceleromenter measures do not increases more than more than twice the previous values
							print('Condizione ACC fatta: EMERGENCY ALERT!')
							url=f'{self.WriteBaseUrl}{patient["apikeyWrite"]}&field4=1' #for collecting panic attack event
							print(url)
							msg={"patientID":patient["patientID"],"alertStatus":1}
							topicTelegram=self.baseTopic+str(patient["patientID"])+'/telegram'
	
							self.client.myPublish(topicTelegram,msg)
							sleep_msg ={'msg':'sleep'}
							topicTS = self.baseTopic+str(patient["patientID"])+'/PA'
							self.client.myPublish(topicTS,sleep_msg)
							time.sleep(15)
							r=requests.get(url) #ThingSpeak request to store panic attack event
							
					
					patient['lastHR']=median(patient["windowHR"])
					patient['lastACC']=median(patient["windowACC"])
		
					print(f'HR current window:\n {patient["windowHR"]}')
					print(f"HR current median: {patient['lastHR']}")
					
					print(f'Acceleration current window:\n {patient["windowACC"]}')
					print(f"Acceleration current median: {patient['lastACC']}")
					
	def CatalogCommunication(self):
		r=requests.get(self.CATALOG_URL+f'/broker') #retrieve broker/port 
		if self.broker and self.port:
			
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

		r=requests.get(self.CATALOG_URL+f'/token') #retrieve token
		if self.token: 
			if not self.token== r.json(): #if token is changed
				self.token=r.json() # token is updated
		else:
			self.token=r.json()

		#patients information
		r=requests.get(self.CATALOG_URL+f'/patients') 
		body2=r.json() 
		patient_ID_list=[ID["patientID"] for ID in self.dict] #list of patient ID already retrieved and present in self.dict
		for item in body2:
			if not item["patientID"] in patient_ID_list: #if the patient ID is not present in self.dict, it's added
				new_patient={"patientID":item["patientID"], "channel":item["channel"], "apikeyWrite": item["apikey"][0],"apikeyRead": item["apikey"][1],"windowHR":[],"windowACC":[]}
				self.dict.append(new_patient)
			else: #if it is present
				for patient in self.dict:
					if patient["patientID"]==item["patientID"]:
						patient["apikeyWrite"]=item["apikey"][0] #...apikey and channelID are updated
						patient["apikeyRead"]=item["apikey"][1]
						patient["channel"]=item["channel"]	
			

if __name__=="__main__":
	#sys.argv[1] is Configuration_file.json				      
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	clientID = conf["PatientControl"]["clientID"]
	fp.close()
	
	PC=PatientControl(CATALOG_URL,bT,clientID)
	PC.CatalogCommunication()
	tic=time.time()
	while True:
		if time.time()-tic>=(60*5): #every 5 minutes broker, port, token and patient information are retrieved and control strategy is performed
			PC.CatalogCommunication()
			PC.controlStrategy()
			tic=time.time()
	
	
	
