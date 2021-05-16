from MyMQTT import *
import json
import requests
from datetime import datetime
import sys

# from datetime import strftime
#is an MQTT subscriber that receives patient measurements and upload them on Thinkspeak through REST Web Services (consumer). 
# It works as a MQTT publisher for sending data from storage (ThingSpeak) to the “Data Analysis”. 

class ThingSpeakGateway():
	def __init__(self,clientID,endTopic):
		self.clientID = clientID
		self.endTopic = endTopic
		self.WriteBaseUrl="https://api.thingspeak.com/update?api_key="
		self.ReadBaseUrl="https://api.thingspeak.com/channels/"
		#1264245/feeds.json?api_key=8GB6GHSYYF6AIB98&results=2"
		self.client=MyMQTT(clientID,self.broker,self.port,self) #cration of MQTT subscribers

	def start(self):
		self.client.start()
		for t in endTopic:
			topic='iSupport/+/sensors/'+t
			self.client.mySubscribe(topic)

	def notify(self,topic,payload):
		#receive from DC and send them to TS 
		payload=json.loads(payload)
		topic=topic.split('/')
		id=int(topic[1]) #patientID
		print(id)
		for i,p in enumerate(self.patients):# "Temperature" and "Humidity"??
			if p==id:
				print(f'\npatient number: {p}\n')
				if topic[3]=='HeartRate':
					number=1					
				elif topic[3]=='Accelerometer':
					number=2					
				elif topic[3]=='Motion':
					number=3
					
				url=f'{self.WriteBaseUrl}{self.apikeysW[i]}&field{str(number)}={str(payload["e"][0]["value"])}'	
				r=requests.get(url)
				print(url)
				data_s=datetime.now()
				data=payload["e"][0]["timestamp"].split(' ')
				data=datetime.strptime(data[1],'%H:%M:%S.%f')
				print(f'Waited time: {data_s-data}')
				
	
	# def notifyHandler(self,url,i,payload):
	# 	#every message of each patient have to wait 15s to make the get request for writing on the channel
	# 	while time.time()-self.timestamp[i]>=15:
	# 		print(url)
	# 		data_s=datetime.now()
	# 		r=requests.get(url)
	# 		self.timestamp[i]=time.time()
	# 		print('Waiting for 15s')
	# 		data=payload["e"][0]["timestamp"].split(' ')
	# 		data=datetime.strptime(data[1],'%H:%M:%S.%f')
			
	# 		print(f'Waited time: {data_s-data}')

	def publish(self):
		#sending data from storage (ThingSpeak) to the Data Analysis microservice
		for i,p in enumerate(self.patients):
			print(p)
			#first request: weekly report of average heart rate in time bands of the day
			f=1
			field=f"field{f}"
			url=f'{self.ReadBaseUrl}{self.channels[i]}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
			r=requests.get(url) #retrive one day data
			body=r.json()
			payload_HR=[]
			if body!=-1:
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]: #Not None
						feed={"date":body["feeds"][measure]["created_at"],"value":body["feeds"][measure][field]}
						payload_HR.append(feed)
				f=2
				field=f"field{f}"
				url=f'{self.ReadBaseUrl}{self.channels[i]}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
				r=requests.get(url) #retrive one day data
				body=r.json()
				payload_ACC=[]
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]: #Not None
						feed={"date":body["feeds"][measure]["created_at"],"value":body["feeds"][measure][field]}
						payload_ACC.append(feed)
				f=3
				field=f"field{f}"
				url=f'{self.ReadBaseUrl}{self.channels[i]}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
				r=requests.get(url) #retrive one day data
				body=r.json()
				payload_MOT=[]
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]: #Not None
						feed={"date":body["feeds"][measure]["created_at"],"value":body["feeds"][measure][field]}
						payload_MOT.append(feed)
				topic=f'iSupport/{p}/statistics/weekly'
				print(topic)
				payload={'HeartRate':payload_HR,'Accelerometer':payload_ACC,'Motion':payload_MOT}
				self.client.myPublish(topic, payload)

				f=4
				field=f"field{f}"
				url=f'{self.ReadBaseUrl}{str(self.channels[i])}/fields/{f}.json?api_key={self.apikeysR[0]}&days=1' 
				r=requests.get(url) #retrive one day data
				body=r.json()
				numberPA=0
				for measure in range(len(body["feeds"])):
					if body["feeds"][measure][field]:
						numberPA+=1
				payload={'Number of panik attack':numberPA}
				topic=f'iSupport/{p}/statistics/monthly'
				self.client.myPublish(topic, payload)

	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(self.CATALOG_URL+f'/broker') 
		if self.broker and self.port:
			if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #if the broker is changed
				self.broker = r.json()["IPaddress"]
				self.port = r.json()["port"]
				self.client.stop()
				self.client=MyMQTT(self.clientID,self.broker,self.port,self)
				self.start()	
		else:
			print('else CatalogCommunication')
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client=MyMQTT(self.clientID,self.broker,self.port,self)
			self.start()

		r=requests.get(CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		for item in body2:
			for i,patient in enumerate(self.patients):
				if patient == int(item["patientID"]):
					if not item["apikey"][0] == self.apikeysW[i]:
						self.apikeysW[i] = item["apikey"][0]
					if not item["apikey"][1] == self.apikeysR[i]:
						self.apikeysR[i] = item["apikey"][1]
					if not item["channel"] == self.channels[i]:
						self.channels[i] = item["channel"]
				else:
					self.apikeysW.append(item["apikey"][0])
					self.apikeysR.append(item["apikey"][1])
					self.patients.append(int(item["patientID"]))
					self.channels.append(item["channel"])	
		# self.timestamp=len(self.patients)*[0]
		# print(self.timestamp)	

if __name__=="__main__":
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	clientID=conf["ThingSpeakAdaptor"]["clientID"]
	endTopic = conf["ThingSpeakAdaptor"]["endTopic"]
	fp.close()

	gateway=ThingSpeakGateway(clientID,endTopic)
	
	flag=True
	while True:
		today= datetime.now()
		gateway.CatalogCommunication()
		if today.hour==17 and flag: #Monday condition, It has to enter in the condition once a day
			gateway.publish()
			flag=False
		elif today.hour==0: #Next day the flag is restored to True
			flag=True
	get.stop()
