import json
import time
import requests
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardButton, InlineKeyboardMarkup
import sys
from myMQTT import *
import urllib.request

class MQTTbot:
	def __init__(self,CATALOG_URL,baseTopic,endTopic,clientID):
		self.CATALOG_URL = CATALOG_URL
		self.baseTopic = baseTopic
		self.endTopic=endTopic
		self.clientID=clientID
		self.dict=[]
		self.ReadBaseUrl="https://api.thingspeak.com/channels/"
		
		#initialization for token, broker and port
		self.token=0
		self.broker=''
		self.port=0
		
		#message structure
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
						
						if r.status_code == 200: #if POST request succeed
							self.bot.sendMessage(chat_ID, text=f"Patient {message} connected with your bot.")
							flag1 = 1
					
					flag=1
			if flag == 0 or flag1 == 0: #if the patientID was not found or if patientID was found but post request does not succeed  
				self.bot.sendMessage(chat_ID, text="No Patient found, retry\nEnter the patientID:")

		elif message == "/status": #commad to visualise HR, acclerometer measurments and number of panic attack
			buttons=[] 
			for patient in self.dict:
				if chat_ID in patient["chatID"]:
					buttons.append([InlineKeyboardButton(text=f'patient {patient["patientID"]}',callback_data=f'{patient["patientID"]}')])
			keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) 
			self.bot.sendMessage(chat_ID, text='Choose a patient', reply_markup=keyboard) #one button for each patient under doctor's care is shown

		else:
			self.bot.sendMessage(chat_ID, text="Command not supported")

	def on_callback_query(self,msg):
		query_ID , chat_ID , query_data = telepot.glance(msg,flavor='callback_query') 
		if query_data.isdigit(): #if patientID is chosen 
			buttons=[[InlineKeyboardButton(text=f'Daily',callback_data=f'daily {query_data}')],[InlineKeyboardButton(text=f'Month',callback_data=f'month {query_data}')]]
			keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
			self.bot.sendMessage(chat_ID, text='Choose time', reply_markup=keyboard) #"daily" and "month" button are displayed 
		else: #if daily or month are clicked 
			query_data=query_data.split(' ')
			if query_data[0]=='daily':
				for patient in self.dict:
					if patient["patientID"]==query_data[1]:
						url=f'{self.ReadBaseUrl}{patient["channel"]}/charts/1?bgcolor=%23ffffff&color=%23d62020&days=1&dynamic=true&type=line' 
						url2=f'{self.ReadBaseUrl}{patient["channel"]}/charts/2?bgcolor=%23ffffff&color=%23d62020&days=1&dynamic=true&type=line' 
						url3=f'{self.ReadBaseUrl}{patient["channel"]}/charts/4?bgcolor=%23ffffff&color=%23d62020&days=1&dynamic=true&type=line' 
						self.bot.sendMessage(chat_ID,text=f"<a href='{url}'>Heart Rate</a>\n<a href='{url2}'>Accelerometer</a>\n<a href='{url3}'>Panik Attack</a>",parse_mode='HTML',disable_web_page_preview = False) #links of charts on thinspeak are shown 

			elif query_data[0] == 'month':
				for patient in self.dict:
					if patient["patientID"]==query_data[1]:
						url=f'{self.ReadBaseUrl}{patient["channel"]}/charts/1?bgcolor=%23ffffff&color=%23d62020&days=30&dynamic=true&type=line' 
						url2=f'{self.ReadBaseUrl}{patient["channel"]}/charts/2?bgcolor=%23ffffff&color=%23d62020&days=30&dynamic=true&type=line' 
						url3=f'{self.ReadBaseUrl}{patient["channel"]}/charts/4?bgcolor=%23ffffff&color=%23d62020&days=30&dynamic=true&type=line' 
						self.bot.sendMessage(chat_ID,text=f"<a href='{url}'>Heart Rate</a>\n<a href='{url2}'>Accelerometer</a>\n<a href='{url3}'>Panik Attack</a>",parse_mode='HTML',disable_web_page_preview = False) #links of charts on thinspeak are shown

			
	def notify(self,topic,message): # it receives messages from PatientControl in case of panic attack
		payload=json.loads(message)
		topic=topic.split('/')
		id=int(topic[1]) #patientID

		for patient in self.dict:
			if int(patient["patientID"])==id:
				if "chatID" in patient: #if the patient has already a doctor/care giver who needs to be notified
					chat_IDs=patient["chatID"]
					tosend=f'ATTENTION: The patient {patient["patientID"]}\n{self.__message["alert"]}, you should {self.__message["action"]}'
					for c in chat_IDs: #send allert message to all present chatiDs
						self.bot.sendMessage(c, text=tosend)				

	def CatalogCommunication(self):
		r=requests.get(self.CATALOG_URL+f'/broker') #retrieve broker/port 
		if self.broker and self.port: #if broker and port already exist...
			if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #check if the broker/port is changed...
				self.broker = r.json()["IPaddress"]
				self.port = r.json()["port"]
				self.client.stop() #stop the previous client and 
				self.client=MyMQTT(self.clientID,self.broker,self.port,self) #create and start new client and subscribe to topic
				self.client.start() 
				TOPIC = f"{self.baseTopic}+/+{self.endTopic}"
				self.client.mySubscribe(TOPIC)	
		else: #create and start new client and subscribe to topic
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
				MessageLoop(self.bot, {'chat': self.on_chat_message, 'callback_query': self.on_callback_query}).run_as_thread()
		else: #create and start new bot
			self.token=r.json()
			self.bot = telepot.Bot(self.token)
			MessageLoop(self.bot, {'chat': self.on_chat_message, 'callback_query': self.on_callback_query}).run_as_thread()
		
		#retrieve patient ID and telegramIDs
		r=requests.get(self.CATALOG_URL+f'/patients') 
		body2=r.json() 
		patient_ID_list=[ID["patientID"] for ID in self.dict] #list of patient ID already retreived and present in self.dict
		for item in body2:
			if not item["patientID"] in patient_ID_list: #if the patient ID is not present in self.dict, it is added
				new_patient={"patientID":item["patientID"],"chatID":item["telegramIDs"],"channel": item["channel"],"apikey":item["apikey"][1]} #status: 0 off, status: 1 on
				self.dict.append(new_patient)
			else: #if patient already in list_dict...
				for patient in self.dict:
					if patient["patientID"]==item["patientID"]:
						patient["chatID"]=item["telegramIDs"] #... chatIDs are updated


if __name__ == "__main__":
	# sys.argv[1] is the Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	endTopic=conf["TelegramBot"]["endTopic"]
	clientID=conf["TelegramBot"]["clientID"]
	fp.close()

	tb=MQTTbot(CATALOG_URL,bT,endTopic,clientID)
	while True: #every 120s token/broker/port and patient "chatID" are retrieved
		tb.CatalogCommunication()
		time.sleep(120)
