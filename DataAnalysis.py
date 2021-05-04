import json
from myMQTT import *
import requests
import statistics
# it is a block that has the task of obtaining statistical data on the wellness of the patient. It provides information such as:
# - weekly report of average heart rate in time bands of the day; 
# - weekly activity status (percentage of over threshold movement looking in pair heart rate and accelerometer measurements) (Flow chart 1);
# - recurrence of panic attacks (example: number of panic attack in the last month);
# - weekly report of how long the person has been in the bedroom, using data from a motion sensor on the bedroom’s door (Flow chart 2).
# It works as an MQTT subscriber that recieves data from ThingSpeak Adaptor and as a MQTT publisher that sends processed data to Node-RED.
# CATALOG_URL="http://127.0.0.1:8080"
clientID="DataAnalysisMS"
# DAtopicS="iSupport/+/statistics/#" 
# DATtopicP_base="iSupport/"

class DataAnalysis():
	def __init__(self,CATALOG_URL,topic_base):
		self.DATtopicP_base = topic_base
		self.DAtopicS = topic_base + '+/statistics/#' #/weekly and /monthly
		self.list_dict=[]
		self.CatalogCommunication()
		self.WriteBaseUrl="https://api.thingspeak.com/update?api_key="
		self.ReadBaseUrl="https://api.thingspeak.com/channels/"
		self.client=MyMQTT(clientID,self.broker,self.port,self) #cration of MQTT subscribers

	def start(self):
		self.client.start() 
		self.client.mySubscribe(self.DAtopicS)

	def stop(self):
		self.client.stop()
	#patient={"patientID":int(item["patientID"]),"apikey":item["apikey"],"channel":item["channel"],"day":0,"min_value":[],"max_value":[],"mean_value":[]}	
			
	def notify(self,topic,payload):
		print('Hello')
		#It works as an MQTT subscriber that recieves data from ThingSpeak Adaptor
		#weekly report of average heart rate in time bands of the day; 3 Time bands
		payload=json.loads(payload)
		id=int(topic.split("/")[1])
		for i,pat in enumerate(self.list_dict):
			if id==pat["patientID"]:
				pos=i

		if topic.split("/")[3]=="weekly":
			bodyHR=payload["HeartRate"]
			print(f'\nHR: {bodyHR}\n')
			bodyACC=payload["Accelerometer"]
			print(f'ACC:{bodyACC}\n')
			bodyMOT=payload["Motion"]
			self.list_dict[pos]["Weekly Measurements"]["day"]=self.list_dict[pos]["Weekly Measurements"]["day"]+1
			for feed in bodyHR:
				date=feed["date"].split("T")[1].split(":") #we care about the hour (date[0])
				if int(date[0])<=8:
					if self.list_dict[pos]["Weekly Measurements"]["min_value"][0]>float(feed["value"]):
						self.list_dict[pos]["Weekly Measurements"]["min_value"][0]=float(feed["value"])
					if self.list_dict[pos]["Weekly Measurements"]["max_value"][0]<float(feed["value"]):
						self.list_dict[pos]["Weekly Measurements"]["max_value"][0]=float(feed["value"])
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][0]=self.list_dict[pos]["Weekly Measurements"]["mean_value"][0]+float(feed["value"])
				elif int(date[0])<=19:
					if self.list_dict[pos]["Weekly Measurements"]["min_value"][1]>float(feed["value"]):
						self.list_dict[pos]["Weekly Measurements"]["min_value"][1]=float(feed["value"])
					if self.list_dict[pos]["Weekly Measurements"]["max_value"][1]<float(feed["value"]):
						self.list_dict[pos]["Weekly Measurements"]["max_value"][1]=float(feed["value"])
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][1]=self.list_dict[pos]["Weekly Measurements"]["mean_value"][1]+float(feed["value"])
				else: #int(date[0])<24:
					if self.list_dict[pos]["Weekly Measurements"]["min_value"][2]>float(feed["value"]):
						self.list_dict[pos]["Weekly Measurements"]["min_value"][2]=float(feed["value"])
					if self.list_dict[pos]["Weekly Measurements"]["max_value"][2]<float(feed["value"]):
						self.list_dict[pos]["Weekly Measurements"]["max_value"][2]=float(feed["value"])
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][2]=self.list_dict[pos]["Weekly Measurements"]["mean_value"][2]+float(feed["value"])
			
			if len(bodyACC)==len(bodyHR)-1: 
				bodyHR.pop()
			#chiedere: dobbiamo studiare anche la possibilità che uno dei due sensori si stacca e adesempio la registrazione è interrotta per mezz"ora?
			
			for feedACC,feedHR in bodyACC,bodyHR:
				if float(feedACC["value"])>2: #first threshold
					temp.append(float(feedHR))
				else:
					if len(temp)>=5:  #consider only at least 5 samples length activity over threshold
						#evaluate the activity status:
						if statistics.mean(temp)<80:
							self.list_dict[pos]["activity"][0]+=len(temp)
						elif statistics.mean(temp)<120:
							self.list_dict[pos]["activity"][1]+=len(temp)
						else:
							self.list_dict[pos]["activity"][2]+=len(temp)
					temp=[]	
			
			#chiedere: abbiamo un solo motion sensor 
			#weekly report of how long the person has been in the bedroom, using data from a motion sensor on the bedroom’s door 
			self.list_dict[pos]["bedroomstatus"][1]+=len(bodyMOT) #total number of samples
			for item in bodyMOT:
				if item["value"]==1:
					self.list_dict[pos]["bedroomstatus"][0]+=1 #number of Motion detection

			if self.list_dict[pos]["day"]==7:
				self.publish(id,"weekly")
				self.list_dict[pos]["Weekly Measurements"]["min_value"]=[1000]*3
				self.list_dict[pos]["Weekly Measurements"]["max_value"]=[0]*3
				self.list_dict[pos]["Weekly Measurements"]["mean_value"]=[0]*3
				self.list_dict[pos]["Weekly Measurements"]["day"]=0
				self.list_dict[pos]["Weekly Measurements"]["bedroomstatus"]=[0]*2
				self.list_dict[pos]["Weekly Measurements"]["activity"]=[0]*3

		else: #recurrence of panic attacks 
			self.list_dict[pos]["Monthly Measurements"]["day"]+=1
			self.list_dict[pos]["Monthly Measurements"]["panik attack"]+=payload["Number of panik attack"]
			if self.list_dict[pos]["Monthly Measurements"]["day"]==30:
				self.publish(id,"monthly")
				self.list_dict[pos]["Monthly Measurements"]["day"]=0
			
	def publish(self,id,command):
		i= [i for i,pat in enumerate(self.list_dict) if id==pat["patientID"]] #it is unique
		topic=self.DATtopicP_base+str(i)+"/nodered"
		
		if command=='weekly':
			activity=self.list_dict[i]["Weekly Measurements"]["activity"]
			bed=self.list_dict[i]["Weekly Measurements"]["bedroom status"]
			payload={"patientID":id,
			"average heart rate":{
				"min_value":self.list_dict[i]["Weekly Measurements"]["min_value"],
				"max_value":self.list_dict[i]["Weekly Measurements"]["max_value"],
				"mean_value":self.list_dict[i]["Weekly Measurements"]["mean_value"]
				},
			"activity status":[a/sum(activity)*100 for a in activity],
			"bedroomMotion":bed[0]/bed[1]
			}
			self.client.myPublish(topic, payload) 

		elif command=='monthly':
			payload={"patientID":id,
			"Panik Attack":self.list_dict[i]["Monthly Measurements"]["panik attack"]
			}
			self.client.myPublish(topic, payload)
			

	
	def CatalogCommunication(self):
		#Retriving information about MB
		r=requests.get(self.CATALOG_URL+f"/broker") 
		body=r.json()
		self.broker=body["IPaddress"]
		self.port=body["port"]
		#Retriving information about ThingSpeak API keys
		r=requests.get(self.CATALOG_URL+f"/patients") 
		body2=r.json() #lista di dizionari
		for item in body2:
			patient={"patientID":int(item["patientID"]),
			 	"PatientInfo":{
					  "apikey":item["apikey"],
					  "channel":item["channel"]
				 		},
				 "Weekly Measurements":{ 
						"day":0,
						"min_value":[1000]*3,
						"max_value":[0]*3,
						"mean_value":[0]*3,
						"activity":[0]*3,
						"bedroomstatus":[0,0]},
				"Monthly Measurements":{
					"day":0,
					"panik attack":0
					 }
				}	
			self.list_dict.append(patient)
			

if __name__=="__main__":
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 

	D=DataAnalysis(CATALOG_URL,bT)
	D.start()
	while True:
		pass