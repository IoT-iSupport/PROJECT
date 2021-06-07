import json
from myMQTT import *
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

class DataAnalysis():
	def __init__(self,CATALOG_URL,topic_base,endTopic,clientID):
		self.CATALOG_URL = CATALOG_URL
		self.DATtopicP_base = topic_base
		self.endTopic = endTopic
		self.DAtopicS = topic_base + '+/statistics/#' #/weekly and /monthly
		self.clientID=clientID
		self.list_dict=[]
		self.WriteBaseUrl="https://api.thingspeak.com/update?api_key="
		self.ReadBaseUrl="https://api.thingspeak.com/channels/"
		
		#initialization for borken and port
		self.broker=''
		self.port= 0 

	def start(self): #start client and subscribes to topics
		self.client.start() 
		self.client.mySubscribe(self.DAtopicS)

	def stop(self):
		self.client.stop()
			
	def notify(self,topic,payload): #It works as an MQTT subscriber that recieves data from ThingSpeak Adaptor

		payload=json.loads(payload)
		id=int(topic.split("/")[1]) #patient ID
		
		#search the patient in the list created with the catalog communication
		for i,pat in enumerate(self.list_dict): 
			if id==pat["patientID"]:
				pos=i 
		#weekly report 
		if topic.split("/")[3]=="weekly":
			#weekly report of average heart rate 
			bodyHR=payload["HeartRate"]
			bodyACC=payload["Accelerometer"]
			bodyMOT=payload["Motion"]
			self.list_dict[pos]["Weekly Measurements"]["day"] += 1 
			for feed in bodyHR:
				date=feed["date"].split("T")[1].split(":") #we care about the hour (date[0])
				#the HR measureament are divided into 3 time slots (0-8/8-19/19-24):
				if int(date[0])<=8: 
					#summing all the measureament (the division for obtaining the mean value is done before publishing )
					self.list_dict[pos]["Weekly Measurements"]["number"][0] += 1
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][0] +=float(feed["value"])
				elif int(date[0])<=19:
					self.list_dict[pos]["Weekly Measurements"]["number"][1] += 1
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][1] += float(feed["value"])
				else: #int(date[0])<24:
					self.list_dict[pos]["Weekly Measurements"]["number"][2] += 1
					self.list_dict[pos]["Weekly Measurements"]["mean_value"][2] += float(feed["value"])
			
			#activity report of the patient
			temp = []
			for feedACC,feedHR in zip(bodyACC,bodyHR):
				if float(feedACC["value"])>2: #first threshold
					temp.append(float(feedHR["value"]))
				else:
					if len(temp)>=5:  #consider at least 5 consecutive samples length activity over threshold
						#evaluate the activity status:
						if statistics.mean(temp)<80: #low intensity
							self.list_dict[pos]["Weekly Measurements"]["activity"][0]+=len(temp)
						elif 80<statistics.mean(temp)<120: #medium intensity
							self.list_dict[pos]["Weekly Measurements"]["activity"][1]+=len(temp)
						else: #high intensity
							self.list_dict[pos]["Weekly Measurements"]["activity"][2]+=len(temp)
						temp=[]	
					else:
						temp=[]	
			if temp !=[]: #last window is not evalueted because of an if condition is satisfied - so the temp is not emptied
				if len(temp)>5:
					if statistics.mean(temp)<80:
						self.list_dict[pos]["Weekly Measurements"]["activity"][0]+=len(temp)
					elif 80<statistics.mean(temp)<120:
						self.list_dict[pos]["Weekly Measurements"]["activity"][1]+=len(temp)
					else:
						self.list_dict[pos]["Weekly Measurements"]["activity"][2]+=len(temp)

			#weekly report of how long the person has been in the bedroom, using data from a motion sensor on the bedroom’s door 
			self.list_dict[pos]["Weekly Measurements"]["bedroomstatus"][1] += len([float(item["value"]) for item in bodyMOT if item["value"]!=None]) #total number of samples
			self.list_dict[pos]["Weekly Measurements"]["bedroomstatus"][0] = sum([float(item["value"]) for item in bodyMOT if item["value"]!=None]) #None removed

			#the publishing is done after 7 days of analysis - so the observation window are emptied
			if self.list_dict[pos]["Weekly Measurements"]["day"]==7:
				self.publish(id,"weekly") #publish statistics to NODE-RED
				self.list_dict[pos]["Weekly Measurements"]["number"] = [0]*3
				self.list_dict[pos]["Weekly Measurements"]["mean_value"]=[0]*3
				self.list_dict[pos]["Weekly Measurements"]["day"]=0
				self.list_dict[pos]["Weekly Measurements"]["bedroomstatus"]=[0]*2
				self.list_dict[pos]["Weekly Measurements"]["activity"]=[0]*3

		else: #recurrence of panic attacks 
			self.list_dict[pos]["Monthly Measurements"]["day"]+=1
			self.list_dict[pos]["Monthly Measurements"]["panik attack"] += float(payload["Number of panik attack"])
			#the publishing is done after 30 days of analysis
			if self.list_dict[pos]["Monthly Measurements"]["day"]==30:
				self.publish(id,"monthly") #publish to NODE-RED
				self.list_dict[pos]["Monthly Measurements"]["day"]=0			

	def publish(self,id,command):
		i= [int(pos) for pos,pat in enumerate(self.list_dict) if id==pat["patientID"]][0] #it is unique - search of the position of the patient in the list
		topic=self.DATtopicP_base+str(id)+self.endTopic
		if command=='weekly': #weekly report
			#activity report of the patient
			activity = self.list_dict[i]["Weekly Measurements"]["activity"]
			try :
				x =[a/sum(activity)*100 for a in activity] #for avoiding error due to zero division
			except:
				x = [0,0,0]
			
			#weekly report of average heart rate 
			y = []
			for n,m in zip(self.list_dict[i]["Weekly Measurements"]["number"],self.list_dict[i]["Weekly Measurements"]["mean_value"]):
				try :
					y.append(m/n) #for avoiding error due to zero division
				except:
					y.append(0)
			
			#weekly report of how long the person has been in the bedroom
			bed=self.list_dict[i]["Weekly Measurements"]["bedroomstatus"]
			bed_output = bed[0]/bed[1]
			payload={"patientID":id,
			"average heart rate":{
				"mean_value": y
				},
			"activity":x,
			"bedroomMotion":bed_output*100
			}
			self.client.myPublish(topic, payload) 


		elif command=='monthly': #monthly report
			payload2={"patientID":id,
			"Panik Attack": self.list_dict[i]["Monthly Measurements"]["panik attack"]
			}
			self.client.myPublish(topic, payload2)
			

	
	def CatalogCommunication(self): #retrieve broker/port 
		r=requests.get(self.CATALOG_URL+f'/broker') 
		if self.broker and self.port:
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

		#Retriving information about ThingSpeak API keys
		r=requests.get(self.CATALOG_URL+f"/patients") 
		body2=r.json() #lista di dizionari
		patient_ID_list=[identifier["patientID"] for identifier in self.list_dict] #list of patient ID already retrieved and present in self.dict
		
		for item in body2:
			if not int(item["patientID"]) in patient_ID_list: #if the patient ID is not present in self.dict, it's added
				
				patient={"patientID":int(item["patientID"]),
					"PatientInfo":{
						"apikey":item["apikey"],
						"channel":item["channel"]
							},
					"Weekly Measurements":{ 
							"day":0,
							"number":[0]*3,
							"mean_value":[0]*3,
							"activity":[0]*3,
							"bedroomstatus":[0,0]},
					"Monthly Measurements":{
						"day":0,
						"panik attack":0
						}
					}	
				self.list_dict.append(patient) 
				
			else: #if patient already in list_dict...
				for patient in self.list_dict:
					if patient["patientID"]==item["patientID"]:
						patient["PatientInfo"]["apikey"]=item["apikey"] #... update apikey and channel
						patient["PatientInfo"]["channel"]=item["channel"]		
						
if __name__=="__main__":
	#sys.argv[1] is Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	endTopic=conf["DataAnalysis"]["endTopic"]
	clientID=conf["DataAnalysis"]["clientID"]
	fp.close()

	D=DataAnalysis(CATALOG_URL,bT,endTopic,clientID)
	
	while True:
		try:
			D.CatalogCommunication()
		except:
			print('Catalog Communication Failed')
		time.sleep(120) #the Catalog communication is done every two minutes 
