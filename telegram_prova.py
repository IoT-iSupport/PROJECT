import json
import time
import requests
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardButton, InlineKeyboardMarkup

from myMQTT import *
TOPIC="iSupport/+/telegram"
CATALOG_URL='http://127.0.0.1:8080'

class MQTTbot:
	def __init__(self):
		self.dict=[]
		
		self.__message={"alert":"is having a Panik attack","action":"check the situation"}
	
	def on_chat_message(self, msg):
		content_type, chat_type, chat_ID = telepot.glance(msg)
		print(chat_ID)
		message = msg['text']
		flag=0
		if message=="/start":
		   	self.bot.sendMessage(chat_ID, text="Welcome!\nEnter the patientID")
		elif message.isdigit():
			for patient in self.dict:
				if int(patient["patientID"])==int(message):
					r=requests.get(CATALOG_URL+f"/chatIDs/{int(message)}")
					body=r.json()
					patient["chatIDs"]=body["chatIDs"]
					print(self.dict)
					self.bot.sendMessage(chat_ID, text="Added")
					flag=1
			if flag==0:
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
				if "chatIDs" in patient:
					chat_IDs=patient["chatIDs"]
					tosend=f'ATTENTION: The patient {patient["patientID"]}\n{self.__message["alert"]}, you should {self.__message["action"]}'
					for c in chat_IDs:
						self.bot.sendMessage(c, text=tosend)	

	def CatalogCommunication(self):
		#with the catalog, for retriving information
		r=requests.get(CATALOG_URL+f'/broker') 
		body=r.json()
		self.broker=body["IPaddress"]
		self.port=body["port"]
		r=requests.get(CATALOG_URL+f'/token') 
		self.token=r.json()
		r=requests.get(CATALOG_URL+f'/patients') 
		body2=r.json() #lista di dizionari
		for item in body2:
			new_patient={"patientID":item["patientID"]} #status: 0 off, status: 1 on
			self.dict.append(new_patient)
		#creation of the client
		self.client=MyMQTT("telegramBot_iSupport",self.broker,self.port,self)
		self.client.start() 
		self.client.mySubscribe(TOPIC)
		self.bot = telepot.Bot(self.token)
		MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()

if __name__ == "__main__":
	
	tb=MQTTbot()
	input("press a key to start...")
	tb.CatalogCommunication()
	while True:
		pass
