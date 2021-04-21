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
        self.__message={"alert":"","action":""}
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
        #if message=="/start":
        #   self.bot.sendMessage(chat_ID, text="Welcome")
        #else:
        self.bot.sendMessage(chat_ID, text="Command not supported")
        
    def notify(self,topic,message):
        payload=json.loads(payload)
	topic=topic.split('/')
	id=int(topic[1]) #patientID
	print(id)

        for patient in self.dict:
		print(patient["patientID"])
			if int(patient["patientID"])==id:
        		        chat_ID=patient["chatID"]
        
		alert=payload["alert"]
		action=payload["action"]
		tosend=f"ATTENTION: The patient {patient["patientID]}\n{alert}, you should {action}"
		self.bot.sendMessage(chat_ID, text=tosend)
		# for chat_ID in self.chatIDs:
		#     self.bot.sendMessage(chat_ID, text=tosend)

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
			new_patient={"patientID":item["patientID"],"chatID":item["telegramIDs"]} #status: 0 off, status: 1 on
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
