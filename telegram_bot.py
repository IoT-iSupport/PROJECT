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
		self.token=0
		self.broker=''
		self.port=0
		self.__message={"alert":"is having a Panik attack","action":"check the situation"}
	
	def on_chat_message(self, msg):
		content_type, chat_type, chat_ID = telepot.glance(msg)
		print(chat_ID)
		message = msg['text']
		flag,flag1 = 0,0
		if message=="/start":
		   	self.bot.sendMessage(chat_ID, text="Welcome!\nIf you want to add a new patient, enter the patientID:")
		elif message.isdigit():
			for patient in self.dict:
				if int(patient["patientID"])==int(message):
					for item in patient["chatID"]:
						if item == chat_ID:
							self.bot.sendMessage(chat_ID, text=f"Patient {message} ALREADY connected with your bot.")	
							flag1 = 1
					if flag1 == 0:
						catalog_data = {"chatID": chat_ID}
						r=requests.post(self.CATALOG_URL+f"/chatID/{patient['patientID']}",json=catalog_data)
						print(r.status_code)
						if r.status_code == 200:
							self.bot.sendMessage(chat_ID, text=f"Patient {message} connected with your bot.")
							flag1 = 1
					
					flag=1
			if flag == 0 or flag1 == 0:
				self.bot.sendMessage(chat_ID, text="No Patient found, retry\nEnter the patientID:")
		else:
			self.bot.sendMessage(chat_ID, text="Command not supported")


			
	def notify(self,topic,message):
		payload=json.loads(message)
		topic=topic.split('/')
		id=int(topic[1]) #patientID
		#print(id)

		for patient in self.dict:
			print("for")
			if int(patient["patientID"])==id:
				print(int(patient["patientID"]))
				if "chatID" in patient:
					chat_IDs=patient["chatID"]
					tosend=f'ATTENTION: The patient {patient["patientID"]}\n{self.__message["alert"]}, you should {self.__message["action"]}'
					for c in chat_IDs:
						self.bot.sendMessage(c, text=tosend)	

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
				self.client.start() 
				TOPIC = f"{self.baseTopic}+/+{self.endTopic}"
				print(TOPIC)
				self.client.mySubscribe(TOPIC)	
		else:
			print('else CatalogCommunication')
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client=MyMQTT(self.clientID,self.broker,self.port,self)
			self.client.start() 
			TOPIC = f"{self.baseTopic}+/{self.endTopic}"
			print(TOPIC)
			self.client.mySubscribe(TOPIC)

		r=requests.get(self.CATALOG_URL+f'/token')
		if self.token:
			if not self.token== r.json():
				self.token=r.json()
				self.bot = telepot.Bot(self.token)
				MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()
		else:
			self.token=r.json()
			self.bot = telepot.Bot(self.token)
			MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()
		
		r=requests.get(self.CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		patient_ID_list=[ID["patientID"] for ID in self.dict]
		for item in body2:
			if not item["patientID"] in patient_ID_list:
				new_patient={"patientID":item["patientID"],"chatID":item["telegramIDs"]} #status: 0 off, status: 1 on
				self.dict.append(new_patient)
			else: #if patient already in list_dict...
				for patient in self.dict:
					if patient["patientID"]==item["patientID"]:
						patient["chatID"]=item["telegramIDs"] #... update chatID


if __name__ == "__main__":
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	endTopic=conf["TelegramBot"]["endTopic"]
	clientID=conf["TelegramBot"]["clientID"]
	fp.close()

	tb=MQTTbot(CATALOG_URL,bT,endTopic,clientID)
	print(clientID)
	input("press a key to start...")
	while True:
		tb.CatalogCommunication()
		time.sleep(120)
