import json
from MyMQTT import *
import requests
import sys
import statistics
import time
# it is a block that has the task of obtaining statistical data on the wellness of the patient. It provides information such as:
# - weekly report of average heart rate in time bands of the day; 
# - weekly activity status (percentage of over threshold movement looking in pair heart rate and accelerometer measurements) (Flow chart 1);
# - recurrence of panic attacks (example: number of panic attack in the last month);
# - weekly report of how long the person has been in the bedroom, using data from a motion sensor on the bedroom’s door (Flow chart 2).
# It works as an MQTT subscriber that recieves data from ThingSpeak Adaptor and as a MQTT publisher that sends processed data to Node-RED.
# CATALOG_URL="http://127.0.0.1:8080"

# DAtopicS="iSupport/+/statistics/#" 
# DATtopicP_base="iSupport/"

class DataAnalysis():
	def __init__(self,CATALOG_URL,topic_base,clientID):
		self.CATALOG_URL = CATALOG_URL
		self.DATtopicP_base = topic_base
		self.DAtopicS = topic_base + '+/statistics/#' #/weekly and /monthly
		self.clientID=clientID
		self.list_dict=[]
		self.WriteBaseUrl="https://api.thingspeak.com/update?api_key="
		self.ReadBaseUrl="https://api.thingspeak.com/channels/"
		self.broker=''
		self.port= 0 

	def start(self):
		self.client.start() 
		self.client.mySubscribe(self.DAtopicS)

	def stop(self):
		self.client.stop()
	#patient={"patientID":int(item["patientID"]),"apikey":item["apikey"],"channel":item["channel"],"day":0,"min_value":[],"max_value":[],"mean_value":[]}	
			
	def notify(self,topic,payload):
		#It works as an MQTT subscriber that recieves data from ThingSpeak Adaptor

		#weekly report of average heart rate 
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
			self.list_dict[pos]["Weekly Measurements"]["day"] += 1
			for feed in bodyHR:
				date=feed["date"].split("T")[1].split(":") #we care about the hour (date[0])
				#the HR measureament are divided into 3 time slots (0-8/8-19/19-24):
				if int(date[0])<=8: 
					if self.list_dict[pos]["Weekly Measurements"]["min_value"][0]>float(feed["value"]): #greater than
						self.list_dict[pos]["Weekly Measurements"]["min_value"][0]=float(feed["value"])
					if self.list_dict[pos]["Weekly Measurements"]["max_value"][0]<float(feed["value"]): #minor than
						self.list_dict[pos]["Weekly Measurements"]["max_value"][0]=float(feed["value"])
					#summing all the measureament (the division for obtaining the mean value is done before publishing )
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][0]=self.list_dict[pos]["Weekly Measurements"]["mean_value"][0]+float(feed["value"])
				elif int(date[0])<=19:
					if self.list_dict[pos]["Weekly Measurements"]["min_value"][1]>float(feed["value"]):#greater than
						self.list_dict[pos]["Weekly Measurements"]["min_value"][1]=float(feed["value"])
					if self.list_dict[pos]["Weekly Measurements"]["max_value"][1]<float(feed["value"]):#minor than
						self.list_dict[pos]["Weekly Measurements"]["max_value"][1]=float(feed["value"])
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][1]=self.list_dict[pos]["Weekly Measurements"]["mean_value"][1]+float(feed["value"])
				else: #int(date[0])<24:
					if self.list_dict[pos]["Weekly Measurements"]["min_value"][2]>float(feed["value"]):#greater than
						self.list_dict[pos]["Weekly Measurements"]["min_value"][2]=float(feed["value"])
					if self.list_dict[pos]["Weekly Measurements"]["max_value"][2]<float(feed["value"]):#minor than
						self.list_dict[pos]["Weekly Measurements"]["max_value"][2]=float(feed["value"])
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][2]=self.list_dict[pos]["Weekly Measurements"]["mean_value"][2]+float(feed["value"])
			
			#activity report of the patient
			temp = []
			for feedACC,feedHR in zip(bodyACC,bodyHR):
				if float(feedACC["value"])>2: #first threshold
					temp.append(float(feedHR["value"]))
				else:
					if len(temp)>=5:  #consider at least 5 consecutive samples length activity over threshold
						#evaluate the activity status:
						if statistics.mean(temp)<80:
							self.list_dict[pos]["Weekly Measurements"]["activity"][0]+=len(temp)
						elif 80<statistics.mean(temp)<120:
							self.list_dict[pos]["Weekly Measurements"]["activity"][1]+=len(temp)
						else:
							self.list_dict[pos]["Weekly Measurements"]["activity"][2]+=len(temp)
					temp=[]	
			
			#weekly report of how long the person has been in the bedroom, using data from a motion sensor on the bedroom’s door 
			self.list_dict[pos]["Weekly Measurements"]["bedroomstatus"][1]+=len(bodyMOT) #total number of samples
			# for item in bodyMOT:
			# 	if item["value"]==1:
			# 		self.list_dict[pos]["bedroomstatus"][0]+=1 #number of Motion detection
			self.list_dict[pos]["Weekly Measurements"]["bedroomstatus"][0] = sum([float(item["value"]) for item in bodyMOT if item["value"]!=None])

			if self.list_dict[pos]["Weekly Measurements"]["day"]==7:
				self.publish(id,"weekly")
				self.list_dict[pos]["Weekly Measurements"]["min_value"]=[1000]*3
				self.list_dict[pos]["Weekly Measurements"]["max_value"]=[0]*3
				self.list_dict[pos]["Weekly Measurements"]["mean_value"]=[0]*3
				self.list_dict[pos]["Weekly Measurements"]["day"]=0
				self.list_dict[pos]["Weekly Measurements"]["bedroomstatus"]=[0]*2
				self.list_dict[pos]["Weekly Measurements"]["activity"]=[0]*3
			# elif  self.list_dict[pos]["Weekly Measurements"]["day"]==1:
			# 	self.publish(id,"weekly")

		else: #recurrence of panic attacks 
			self.list_dict[pos]["Monthly Measurements"]["day"]+=1
			self.list_dict[pos]["Monthly Measurements"]["panik attack"]+=float(payload["Number of panik attack"])
			if self.list_dict[pos]["Monthly Measurements"]["day"]==30:
				self.publish(id,"monthly")
				self.list_dict[pos]["Monthly Measurements"]["day"]=0
			# elif self.list_dict[pos]["Monthly Measurements"]["day"]==1:
			# 	self.publish(id,"monthly")
			

	def publish(self,id,command):
		i= [int(pos) for pos,pat in enumerate(self.list_dict) if id==pat["patientID"]][0] #it is unique
		topic=self.DATtopicP_base+str(id)+"/nodered"
		print(topic)
		if command=='weekly':
			activity=self.list_dict[i]["Weekly Measurements"]["activity"]
			try :
				x =[a/sum(activity)*100 for a in activity]
			except:
				x = [0,0,0]
			bed=self.list_dict[i]["Weekly Measurements"]["bedroomstatus"]
			bed_output = bed[0]/bed[1]
			payload={"patientID":id,
			"average heart rate":{
				"min_value":self.list_dict[i]["Weekly Measurements"]["min_value"],
				"max_value":self.list_dict[i]["Weekly Measurements"]["max_value"],
				"mean_value":[m/sum(self.list_dict[i]["Weekly Measurements"]["mean_value"]) for m in self.list_dict[i]["Weekly Measurements"]["mean_value"]]
				},
			"activity":x,
			"bedroomMotion":bed_output*100
			}
			self.client.myPublish(topic, payload) 


		elif command=='monthly':
			payload2={"patientID":id,
			"Panik Attack": self.list_dict[i]["Monthly Measurements"]["panik attack"]
			}
			self.client.myPublish(topic, payload2)
			

	
	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(self.CATALOG_URL+f'/broker') 
		if self.broker and self.port:
			print('if CatalogCommunication')
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

		#Retriving information about ThingSpeak API keys
		r=requests.get(self.CATALOG_URL+f"/patients") 
		body2=r.json() #lista di dizionari
		patient_ID_list=[identifier["patientID"] for identifier in self.list_dict]
		
		for item in body2:
			if not int(item["patientID"]) in patient_ID_list: #if patient not in list_dict...
				
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
				self.list_dict.append(patient) #... add patient
			else: #if patient already in list_dict...
				for patient in self.list_dict:
					if patient["patientID"]==item["patientID"]:
						patient["PatientInfo"]["apikey"]=item["apikey"] #... update apikey and channel
						patient["PatientInfo"]["channel"]=item["channel"]			
		print(self.list_dict)
if __name__=="__main__":
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	clientID=conf["DataAnalysis"]["clientID"]
	fp.close()

	D=DataAnalysis(CATALOG_URL,bT,clientID)
	
	while True:
		D.CatalogCommunication()
		time.sleep(120)
