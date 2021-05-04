#is a control strategy that manages the air conditioning system depending on user presence and on time. 
# The room temperature is changed according to the temperature and humidity measurements 
# only if the motion sensor detects the user presence in that room and according to specific times of the day and of the year. 
# Each room is managed by an instance of this strategy.
# It acts as an MQTT subscriber to receive information from the motion sensor of the room and temperature and humidity sensors. 
# It acts as an MQTT publisher to send actuation command to the air conditioning system. 
import json
import requests
from datetime import datetime
from myMQTT import *

clientID='HomeSystemControlMS'

class HomeSystemControl():
	def __init__(self,CATALOG_URL,bt,timeslot,endTopic):
		self.dict=[] # list of patient
		self.CATALOG_URL = CATALOG_URL
		self.baseTopic = bt
		self.timeslot = timeslot
		self.endTopic = endTopic

	def start(self):
		self.client.start()
		for t in self.endTopic:
			topic=f'{self.baseTopic}+/sensors/'+t
			self.client.mySubscribe(topic)

	def notify(self,topic,payload):
		payload=json.loads(payload)
		topic=topic.split('/')
		id=topic[1] #patientID
		for patient in self.dict:
			if patient["patientID"]==id:
				print(f'\npatient number: {patient["patientID"]}\n')
				if topic[3]==self.endTopic[0]:
					patient["Temperature"].append(float(payload["e"][0]["value"]))
					patient["Humidity"].append(float(payload["e"][1]["value"]))
				elif topic[3]==self.endTopic[1]:
					patient["Motion"].append(int(payload["e"][0]["value"]))

	def controlStrategy(self):
		print('Control strategy check')
		for patient in self.dict:
			topicP=f'{self.baseTopic}{patient["patientID"]}/actuators/Air'
			while len(patient["Temperature"])>15:
				patient["Temperature"].pop(0)
			while len(patient["Humidity"])>15:
				patient["Humidity"].pop(0)
			while len(patient["Motion"])>15:
				patient["Motion"].pop(0)
			print(patient["Motion"])	
			print(patient["Humidity"])
			print(patient["Temperature"])
			# controllo finestra temporale di 15min
			if sum(patient["Motion"])==15: #veryfing the patient presence in the room for at least 15 min
				print('Motion check')
				now_time=datetime.today().time()
				now_month=datetime.now().month
				t1=datetime.strptime(self.timeslot[0],"%H:%M").time()
				t2=datetime.strptime(self.timeslot[1],"%H:%M").time()
				if  t1<=now_time<=t2: 
					#Winter:
					if now_month>=10 or now_month<=3: #from October to March         
						#windows condition
						Out=[t for t in patient["Temperature"] if t>22 or t<18] #out of range values
						if len(Out)>=15:
							#publish for the activation of the air conditioner
							msg={"patientID":patient["patientID"],"AirConditionairStatus":1}
							patient["status"]=1
							self.client.myPublish(topicP,msg)
						else:
							Out_u=[u for u in patient["Humidity"] if u>50 or u<40] #out of range values
							if len(Out_u)>=15:
								msg={"patientID":patient["patientID"],"AirConditionairStatus":1}
								patient["status"]=1
								self.client.myPublish(topicP,msg)
					#Summer:
					elif now_month>=4 or now_month<=9: #from April to September
						print('Month check')
						Out=[t for t in patient["Temperature"] if t>26 or t<24] #out of range values
						print(len(Out))
						print(Out)
						if len(Out)>=15:
							#publish for the activation of the air conditioner
							msg={"patientID":patient["patientID"],"AirConditionairStatus":1}
							patient["status"]=1
							print(msg)
							self.client.myPublish(topicP,msg)
						else:
							Out_u=[u for u in patient["Humidity"] if u>60 or u<50] #out of range values
							if len(Out_u)>=15:
								msg={"patientID":patient["patientID"],"AirConditionairStatus":1}
								patient["status"]=1
								print(msg)
								self.client.myPublish(topicP,msg)   
				else: #if it is night
					if patient["status"]==1:
						msg={"patientID":patient["patientID"],"AirConditionairStatus":0}
						print(msg)
						patient["status"]=0
						self.client.myPublish(topicP,msg)  
	
			else: #if the patient is not present
				if patient["status"]==1:
					msg={"patientID":patient["patientID"],"AirConditionairStatus":0}
					patient["status"]=0
					self.client.myPublish(topicP,msg)  

	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(self.CATALOG_URL+f'/broker') 
		body=r.json()
		self.broker=body["IPaddress"]
		self.port=body["port"]
		self.client=MyMQTT(clientID,self.broker,self.port,self) 

		#patients information
		r=requests.get(self.CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		for item in body2:
			new_patient={"patientID":item["patientID"],"Temperature":[],"Humidity":[],"Motion":[],"status":0}
			self.dict.append(new_patient)


if __name__=="__main__":
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	timeslot = ["HomeSystemControl"]["TimeSlot"]
	endTopic = ["HomeSystemControl"]["endTopic"]
	close(fp)

	HSControl=HomeSystemControl(CATALOG_URL,bt,timeslot,endTopic)
	HSControl.CatalogCommunication()
	HSControl.start()
	tic=time.time()
	while True:
		
		if time.time()-tic>=60*5:
			#every 5 minutes the Home comfort is checked 
			HSControl.controlStrategy()
			HSControl.CatalogCommunication() #every 5 minutes Communication with Catalog is repeted (??)
			tic=time.time()

	
