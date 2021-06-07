#is a control strategy that manages the air conditioning system depending on user presence and on time. 
# The room temperature is changed according to the temperature and humidity measurements 
# only if the motion sensor detects the user presence in that room and according to specific times of the day and of the year. 
# Each room is managed by an instance of this strategy.
# It acts as an MQTT subscriber to receive information from the motion sensor of the room and temperature and humidity sensors. 
# It acts as an MQTT publisher to send actuation command to the air conditioning system (device connector). 
import json
import requests
from datetime import datetime
from myMQTT import *
import sys

class HomeSystemControl():
	def __init__(self,CATALOG_URL,bt,clientID,timeslot,endTopicS,endTopicP):
		self.dict=[] # list of patient
		self.CATALOG_URL = CATALOG_URL
		self.baseTopic = bt
		self.endTopicP = endTopicP
		self.clientID=clientID
		self.timeslot = timeslot
		self.endTopicS = endTopicS
		
		#initialization for broker and port
		self.broker=''
		self.port=0

	def start(self):
		self.client.start()
		for t in self.endTopicS:
			topic=f'{self.baseTopic}+/sensors/'+t
			self.client.mySubscribe(topic)

	def notify(self,topic,payload): # It receives data from sensors (device connector)
		payload = json.loads(payload)
		topic = topic.split('/')
		id = topic[1] #patientID
		
		for patient in self.dict:
			if patient["patientID"]==id:
				
				if topic[3]==self.endTopicS[0]:
					patient["Temperature"].append(float(payload["e"][0]["value"]))
					patient["Humidity"].append(float(payload["e"][1]["value"]))
					
				elif topic[3]==self.endTopicS[1]:
					patient["Motion"].append(int(payload["e"][0]["value"]))

	def controlStrategy(self):
		for patient in self.dict:
			print(f'Controlling home enviroment\tPatient ID: {patient["patientID"]}...')
			topicP=f'{self.baseTopic}{patient["patientID"]}/{self.endTopicP}'
			while len(patient["Motion"])>15:
				patient["Motion"].pop(0)
			
			# control of the observation window 
			if sum(patient["Motion"])==15: #veryfing the patient presence in the room for at least 15 min
				print('User presence detected...')
				now_time=datetime.today().time()
				now_month=datetime.now().month
				#If it is night, for saving energy, the Air conditioner system is not activated.
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
							print('Activating Air Conditionair System')
							self.client.myPublish(topicP,msg)
						else:
							Out_u=[u for u in patient["Humidity"] if u>50 or u<40] #out of range values
							if len(Out_u)>=15:
								msg={"patientID":patient["patientID"],"AirConditionairStatus":1}
								patient["status"]=1
								print('Activating Air Conditionair System')
								self.client.myPublish(topicP,msg)
							else:
								patient["status"]=0
								msg={"patientID":patient["patientID"],"AirConditionairStatus":0}
								print('Deactivating Air Conditionair System')
								self.client.myPublish(topicP,msg)
					#Summer:
					elif now_month>=4 or now_month<=9: #from April to September
						Out=[t for t in patient["Temperature"] if t>26 or t<24] #out of range values
						
						if len(Out)>=15:
							#publish for the activation of the air conditioner
							msg={"patientID":patient["patientID"],"AirConditionairStatus":1}
							patient["status"]=1
							print('Activating Air Conditionair System')
							self.client.myPublish(topicP,msg)
						else:
							Out_u=[u for u in patient["Humidity"] if u>60 or u<50] #out of range values
							if len(Out_u)>=15:
								msg={"patientID":patient["patientID"],"AirConditionairStatus":1}
								patient["status"]=1
								print('Activating Air Conditionair System')
								self.client.myPublish(topicP,msg)   
							else:
								patient["status"]=0
								msg={"patientID":patient["patientID"],"AirConditionairStatus":0}
								print('Deactivating Air Conditionair System')
								self.client.myPublish(topicP,msg)

				else: #if it is night
					print('Night mode activated')
					if patient["status"]==1:
						msg={"patientID":patient["patientID"],"AirConditionairStatus":0}
						print(msg)
						patient["status"]=0
						self.client.myPublish(topicP,msg)  
	
			else: #if the patient is not present
				if patient["status"]==1:
					msg={"patientID":patient["patientID"],"AirConditionairStatus":0}
					patient["status"]=0 #the airConditioner is switched off
					print('Switch off Air Conditionair System')
					self.client.myPublish(topicP,msg)  

	def CatalogCommunication(self):
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

		#patients information
		r=requests.get(self.CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		patient_ID_list=[ID["patientID"] for ID in self.dict] #list of patient ID already retrieved and present in self.dict
		for item in body2:
			if not item["patientID"] in patient_ID_list: #if the patient ID is not present in self.dict, it's added
				new_patient={"patientID":item["patientID"],"Temperature":[],"Humidity":[],"Motion":[],"status":0}
				self.dict.append(new_patient)


if __name__=="__main__":
	#sys.argv[1] is Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bt = conf["baseTopic"] 
	clientID=conf["HomeSystemControl"]["clientID"]
	timeslot = conf["HomeSystemControl"]["TimeSlot"]
	endTopicS = conf["HomeSystemControl"]["endTopicS"]
	endTopicP = conf["HomeSystemControl"]["endTopicP"]
	fp.close()

	HSControl=HomeSystemControl(CATALOG_URL,bt,clientID,timeslot,endTopicS,endTopicP)
	HSControl.CatalogCommunication()
	tic=time.time()
	while True:
		
		if time.time()-tic>=60*10:
			#every 10 minutes CatalogCommunication is done and the Home enviroment is controlled 
			try:
				HSControl.CatalogCommunication()
			except:
				print('Catalog Communication Failed')
			HSControl.controlStrategy()
			tic=time.time()

	
