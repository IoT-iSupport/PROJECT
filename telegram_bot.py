import json
import time
import requests
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardButton, InlineKeyboardMarkup

from MyMQTT import *
TOPIC="iSupport/+/telegram"

class MQTTbot:
    def __init__(self):
        self.chatIDs=[]
        self.__message={"alert":"is having a Panik attack","action":"check the situation"}
	self.CatalogCommunication()
	self.client=MyMQTT("telegramBot_iSupport",self.broker,self.port,self)
	self.client.start() 
	self.client.mySubscribe(TOPIC)
	self.bot = telepot.Bot(self.token)
	MessageLoop(self.bot, {'chat': self.on_chat_message}).run_as_thread()

    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)
        self.chatIDs.append(chat_ID)
        message = msg['text']
        if message=="/start":
           self.bot.sendMessage(chat_ID, text="Welcome!\nEnter the patientID")
	elif message.isdigit():
		for patient in self.dict:
		if patient["patientID"]==int(message):
			r=requests.get(CATALOG_URL+f"/chatIDs/{int(message)}")
			body=r.json()
			self.dict["chatIDs"]=body["chatIDs"]
			self.bot.sendMessage(chat_ID, text="Added")
		else:
			self.bot.sendMessage(chat_ID, text="No Patient found, retry\nEnter the patientID:")
        else:
    		self.bot.sendMessage(chat_ID, text="Command not supported")
        
    def notify(self,topic,message):
        payload=json.loads(payload)
	topic=topic.split('/')
	id=int(topic[1]) #patientID
	print(id)

        for patient in self.dict:
		print(patient["patientID"])
		if int(patient["patientID"])==id:
			if "chatIDs" in patient.keys():
				chat_IDs=patient["chatIDs"]
				tosend=f"ATTENTION: The patient {patient["patientID]}\n{self.__message["alert"]}, you should {self.__message["action"]}"
				self.bot.sendMessage(chat_IDs[0], text=tosend)
				self.bot.sendMessage(chat_IDs[1], text=tosend)

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
		#print(self.dict)

if __name__ == "__main__":
    
    tb=MQTTbot()
    input("press a key to start...")
    test=MyMQTT("testIoTBot",'test.mosquitto.org',1883,None)
    test.start()
    for i in range(5):
        message={"alert":"is having a Panik attack","action":"check the situation"}
        topic="iSupport/"+str(i)+"/telegram"
        test.myPublish(topic,message)
        time.sleep(3)
