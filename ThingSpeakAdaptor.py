from myMQTT import *
import json
import requests
from datetime import datetime
import sys
import time

# It is an MQTT subscriber that receives patient measurements and upload them on Thinkspeak through REST Web Services (consumer) and as an MQTT subscriber that receives if a panick attack has occurred from Patient Control. 
# It works as a MQTT publisher for sending data from storage (ThingSpeak) to the “Data Analysis”. 


class ThingSpeakGateway():
	def __init__(self,CATALOG_URL,bT,endTopic,PAtopic,clientID):
		self.apikeysW=[]
		self.apikeysR=[]
		self.patients=[]
		self.channels=[]
		self.CATALOG_URL=CATALOG_URL
		self.baseTopic = bT
		self.endTopic=endTopic
		self.PAtopic = PAtopic
		self.clientID=clientID
		
		self.WriteBaseUrl="https://api.thingspeak.com/update?api_key="
		self.ReadBaseUrl="https://api.thingspeak.com/channels/"
		
		#initialisation for broker and port
		self.broker=''
		self.port=0
		self.sleep_dict = []

	def start(self): #it starts the client and subscribes to topics
		self.client.start()
		for t in self.endTopic:
			topic = self.baseTopic + '+/sensors/' + t
			self.client.mySubscribe(topic)
		self.client.mySubscribe(self.PAtopic)

	def notify(self,topic,payload): #It receives measurments from Device Connectors and send them to ThingSpeak 
		payload=json.loads(payload)
		topic=topic.split('/')
		id=int(topic[1]) #patientID
		
		#strategy to solve the limitation of the free version of thingspeak that allows to send data every 15 seconds
		if topic[2] == 'PA': #if a panic attack is registered by Patient Control
			self.sleep_dict.append({'Patient':id,'sleep_time':time.time()}) #it is temporary stored with the corresponding patientID

		for i,p in enumerate(self.patients):
			if int(p)==id:
				for i,patient in enumerate(self.sleep_dict):
					if id == patient['Patient']: #if received measurement belongs to a patient present in sleep_dict 
						t = time.time()-patient['sleep_time']
						#print(f'Sleep MODE - elapsed time: {t}s')
						if t<16: #and if 15 seconds have not elapsed yet
							exit() #exit from notify method and the measurment is not stored in thingspeak
						else:
							self.sleep_dict.pop(i) #Patient is removed from the list, so measurments can be stored again
							break
				#save measurment in the corresponding ThingSpeak field
				if topic[3]=='Body':
					numbers=[1,2]
					url=f'{self.WriteBaseUrl}{self.apikeysW[i]}&field{str(numbers[0])}={str(round(payload["e"][0]["value"],2))}&field{str(numbers[1])}={str(round(payload["e"][1]["value"],3))}'	
				elif topic[3]=='Motion':
					number=3
					url=f'{self.WriteBaseUrl}{self.apikeysW[i]}&field{str(number)}={payload["e"][0]["value"]}'	
				elif topic[3]=='Air':
					numbers=[5,6]
					url=f'{self.WriteBaseUrl}{self.apikeysW[i]}&field{str(numbers[0])}={str(round(payload["e"][0]["value"],2))}&field{str(numbers[1])}={str(round(payload["e"][1]["value"],2))}'	
					
				r=requests.get(url)

	def publish(self): #sending data from storage (ThingSpeak) to the Data Analysis microservice
		for i,p in enumerate(self.patients):
			f=1 #haert rate
			field=f"field{f}"
			url=f'{self.ReadBaseUrl}{self.channels[i]}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
			r=requests.get(url) #retrieve one day data
			body=r.json()
			payload_HR=[]
			if body!=-1: #if HR measurments are retrieved correcly 
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]: # None are removed
						feed={"date":body["feeds"][measure]["created_at"],"value":body["feeds"][measure][field]}
						payload_HR.append(feed)
				
			f=2 #accelerometer measurements
			field=f"field{f}"
			url=f'{self.ReadBaseUrl}{self.channels[i]}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
			r=requests.get(url) #retrive one day data
			body=r.json()
			payload_ACC=[]
			if body!=-1: #if accelerometer measurments are retrieved correcly 
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]: # None are removed
						feed={"date":body["feeds"][measure]["created_at"],"value":body["feeds"][measure][field]}
						payload_ACC.append(feed)
				
			f=3 # motion sensor
			field=f"field{f}"
			url=f'{self.ReadBaseUrl}{self.channels[i]}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
			r=requests.get(url) #retrive one day data
			body=r.json()
			payload_MOT=[]
			if body!=-1: #if motion measurments are retrieved correcly 
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]: # None are removed
						feed={"date":body["feeds"][measure]["created_at"],"value":body["feeds"][measure][field]}
						payload_MOT.append(feed)

			f=5 # temperature measurements
			field=f"field{f}"
			url=f'{self.ReadBaseUrl}{self.channels[i]}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
			r=requests.get(url) #retrive one day data
			body=r.json()
			payload_TEM=[]
			if body!=-1: #if temperature measurments are retrieved correcly 
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]: # None are removed
						feed={"date":body["feeds"][measure]["created_at"],"value":body["feeds"][measure][field]}
						payload_TEM.append(feed)

			f=6 #humidity measurements
			field=f"field{f}"
			url=f'{self.ReadBaseUrl}{self.channels[i]}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
			r=requests.get(url) #retrive one day data
			body=r.json()
			payload_HUM=[]
			if body!=-1: #if humidity measurments are retrieved correcly 
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]: # None are removed
						feed={"date":body["feeds"][measure]["created_at"],"value":body["feeds"][measure][field]}
						payload_HUM.append(feed)
			if not payload_HR==[] and not payload_MOT==[] and not payload_ACC==[] and not payload_TEM==[] and not payload_HUM==[]:
				payload={'HeartRate':payload_HR,'Accelerometer':payload_ACC,'Motion':payload_MOT, 'Temperature':payload_TEM, 'Humidity':payload_HUM}
				topic=f'{self.baseTopic}{p}/statistics/weekly'
				self.client.myPublish(topic, payload) # publish data to DataAnalysis with the topic ".../weekly"
				

			f=4 # number of panic attack
			field=f"field{f}"
			url=f'{self.ReadBaseUrl}{str(self.channels[i])}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
			r=requests.get(url) #retrive one day data
			body=r.json()
			numberPA=0
			if body!=-1: #if number of panic attack are retrieved correcly 
				for measure in range(len(body["feeds"])): 
					if body["feeds"][measure][field]: # None are removed
						numberPA+=1
				payload={'Number of panik attack':numberPA}
				topic=f'{self.baseTopic}{p}/statistics/monthly'
				if not payload == []:
					self.client.myPublish(topic, payload) # publish data to DataAnalysis with the topic ".../monthly"

	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(self.CATALOG_URL+f'/broker') #retrieve broker/port 
		if self.broker and self.port: #if broker and port already exist...
			if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #check if the broker is changed...
				self.broker = r.json()["IPaddress"] #... update broker and port
				self.port = r.json()["port"]
				self.client.stop() #stop the previous client and 
				self.client=MyMQTT(self.clientID,self.broker,self.port,self) #create and start new client
				self.start()	
		else: #create and start new client
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client=MyMQTT(self.clientID,self.broker,self.port,self)
			self.start()
		
		#retrieve patient ID, apikeys and channelID
		r=requests.get(CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		
		for item in body2:
			found = 0
			for i,patient in enumerate(self.patients):
				if patient == int(item["patientID"]): #if the patient ID is already present and apikeys and channellID are changed, those information are updated
					if not item["apikey"][0] == self.apikeysW[i]:
						self.apikeysW[i] = item["apikey"][0]
					if not item["apikey"][1] == self.apikeysR[i]:
						self.apikeysR[i] = item["apikey"][1]
					if not item["channel"] == self.channels[i]:
						self.channels[i] = item["channel"]
					found = 1
			if found == 0: #new patient is added
				self.apikeysW.append(item["apikey"][0])
				self.apikeysR.append(item["apikey"][1])
				self.patients.append(int(item["patientID"]))
				self.channels.append(item["channel"])	

if __name__=="__main__":
	#sys.argv[1] is Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	endTopic = conf["ThingSpeakAdaptor"]["endTopic"]
	PAtopic = conf["ThingSpeakAdaptor"]["Panik Attack topic"]
	clientID=conf["ThingSpeakAdaptor"]["clientID"]
	fp.close()

	gateway=ThingSpeakGateway(CATALOG_URL,bT,endTopic,PAtopic,clientID)
	gateway.CatalogCommunication()
	flag=True
	prev = datetime.now()
	while True:
		today= datetime.now()
		if today.hour==12 and flag: #Monday condition. It has to enter in the condition once a day
			gateway.publish() # once a day it receives data from ThingSpeak and publishes them to Data Analysis
			flag=False
		elif today.hour==0: #Next day the flag is restored to True
			flag=True
		elif today.minute-prev.minute>2:
			try:
				gateway.CatalogCommunication()  #every 2 minutes broker/port and patient information are retrieved
			except:
				print('Catalog Communication failed')
			prev = today
	get.stop()

