import json
import time
import requests
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardButton, InlineKeyboardMarkup
import sys
from MyMQTT import *


class MQTTbot:
	def __init__(self,CATALOG_URL,baseTopic,endTopic,clientID):
		self.CATALOG_URL = CATALOG_URL
		self.baseTopic = baseTopic
		self.endTopic=endTopic
		self.clientID=clientID
		self.dict=[]
		
		#initialization for token, broker and port
		self.token=0
		self.broker=''
		self.port=0
		
		self.__message={"alert":"is having a Panik attack","action":"check the situation"}
	
	def on_chat_message(self, msg): #method to handle the incoming messages
		content_type, chat_type, chat_ID = telepot.glance(msg)
		message = msg['text']
		flag,flag1 = 0,0
		if message=="/start":
		   	self.bot.sendMessage(chat_ID, text="Welcome!\nIf you want to add a new patient, enter the patientID:")
			
		elif message.isdigit(): # if the incoming message is the patientID
			for patient in self.dict:
				if int(patient["patientID"])==int(message):
					for item in patient["chatID"]:
						if item == chat_ID: #check if the chatID is already linked to the patient in the Catalog
							self.bot.sendMessage(chat_ID, text=f"Patient {message} ALREADY connected with your bot.")	
							flag1 = 1
					if flag1 == 0: #if the chatID is not linked to the patients yet
						catalog_data = {"chatID": chat_ID}
						patient["chatID"].append(chat_ID)
						r=requests.post(self.CATALOG_URL+f"/chatID/{patient['patientID']}",json=catalog_data)
						print(r.status_code)
						if r.status_code == 200: #if the POST request succeed
							self.bot.sendMessage(chat_ID, text=f"Patient {message} connected with your bot.")
							flag1 = 1
					
					flag=1
			if flag == 0 or flag1 == 0: #if the patientID was not found or post the request does not succeed  
				self.bot.sendMessage(chat_ID, text="No Patient found, retry\nEnter the patientID:")
		else:
			self.bot.sendMessage(chat_ID, text="Command not supported")


			
	def notify(self,topic,message): # receive messages from PatientControl in case of panic attack
		payload=json.loads(message)
		topic=topic.split('/')
		id=int(topic[1]) #patientID
		#print(id)

		for patient in self.dict:
			print("for")
			if int(patient["patientID"])==id:
				print(int(patient["patientID"]))
				if "chatID" in patient: #if the patient has already a doctor/care giver who needs to be notified
					chat_IDs=patient["chatID"]
					tosend=f'ATTENTION: The patient {patient["patientID"]}\n{self.__message["alert"]}, you should {self.__message["action"]}'
					for c in chat_IDs: #send message to all present chatiDs
						self.bot.sendMessage(c, text=tosend)	

	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(self.CATALOG_URL+f'/broker') #retrieve broker/port 
		if self.broker and self.port: #if broker and port already exist...
			print('if CatalogCommunication')
			if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #check if the broker/port is changed...
				self.broker = r.json()["IPaddress"]
				self.port = r.json()["port"]
				self.client.stop() #stop the previous client and 
				self.client=MyMQTT(self.clientID,self.broker,self.port,self) #create and start new client and subscribe to topic
				self.client.start() 
				TOPIC = f"{self.baseTopic}+/+{self.endTopic}"
				self.client.mySubscribe(TOPIC)	
		else: #create and start new client and subscribe to topic
			print('else CatalogCommunication')
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client=MyMQTT(self.clientID,self.broker,self.port,self)
			self.client.start() 
			TOPIC = f"{self.baseTopic}+/{self.endTopic}"
			self.client.mySubscribe(TOPIC)

		#retrieve token
		r=requests.get(self.CATALOG_URL+f'/token')
		if self.token: #if token already exists...
			if not self.token== r.json(): #check if the token is changed...
				self.token=r.json() # update token
				self.bot = telepot.Bot(self.token) #create and start new bot
				MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()
		else: #create and start new bot
			self.token=r.json()
			self.bot = telepot.Bot(self.token)
			MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()
		
		#retrieve patient ID and telegramIDs
		r=requests.get(self.CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		patient_ID_list=[ID["patientID"] for ID in self.dict] #list of patient ID already retreived and present in self.dict
		for item in body2:
			if not item["patientID"] in patient_ID_list: #if the patient ID is not present in self.dict, it is added
				new_patient={"patientID":item["patientID"],"chatID":item["telegramIDs"]} #status: 0 off, status: 1 on
				self.dict.append(new_patient)
			else: #if patient already in list_dict...
				for patient in self.dict:
					if patient["patientID"]==item["patientID"]:
						patient["chatID"]=item["telegramIDs"] #... update chatID


if __name__ == "__main__":
	# command line argument in position 1 is the Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	endTopic=conf["TelegramBot"]["endTopic"]
	clientID=conf["TelegramBot"]["clientID"]
	fp.close()

	tb=MQTTbot(CATALOG_URL,bT,endTopic,clientID)
	input("press a key to start...")
	while True: #every 120s retrieve token/broker/port and patient "chatID"
		tb.CatalogCommunication()
		time.sleep(120)
