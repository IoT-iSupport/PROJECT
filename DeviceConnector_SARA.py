import json
from datetime import datetime
from myMQTT import *
import random
import threading
import requests
import numpy as np
from random import choice
import sys

# CATALOG_URL='http://127.0.0.1:8080'
# patient=1

#codice DeviceConnector2 su git_hub ha degli errori--> correzioni:
#1. if self.broker... in MQTTinfoRequest non funziona perchè devono esistere già self.broker e self.port; provo a mettere la prima richiesta di broker e port nell'init e poi modifco la funzione per connettersi periodicamnete al Catalog, dc.RESTCommunication(sys.argv[2]) l'ho spostato fuori dal while perchè se no self.t non esiste per fare lo start() e ho messo lo start() nel main
# Si potrebbero inizializzare self.broker e self.port nel main e lasciare il codice di prima però c'è sempre il self.client.stop() che implica che un client esista già

#Ho fatto circa le stesse modifiche anche negli altri script che comunicano con il Catlog ma negli altri c'è il problema della request per i pazienti (ex LightShift: se ad ogni comunicazione con Catalog facessi l'append a self.dict aggiungerei dei pazienti che ci sono già; se svuotassi il self.dict dentro CatalogCommunication allorora sovrascriverei le info sullo status. Ho pensato di controllare se il paz è già in self.dict e se lo è aggiorno il "LightsSchedule" che potrebbe cambiare(?) e il resto lo lascio così se non c'è faccio append). Ho fatto circa gli stessi ragionamenti ragionamenti anche oer gli altri script.

#cose da correggere qualisiasi strada sceglieremo:
# for topic in self.t["topic"] nello start(): non va bene perchè self.t non ha la chiave topic
# elif d["measureType"]==['Heart Rate'] nel publish: 'HeartRate' senza spazio
# CONNECTED_DEVICES non è poi visto in publish quindi ho messo self.connected_devices
#  r.json()["IPandress"] IPaddress
# non close(fp) ma fp.close()
#patientID = conf["DeviceConnector"]["patientID"] aggiunto conf

class DeviceConnector():
	def __init__(self,CATALOG_URL,clientID,patient,baseTopic,linesREST,linesSPORT):
		self.linesREST = linesREST
		self.linesSPORT = linesSPORT
		self.patient = patient
		self.clientID = clientID
		self.CATALOG_URL = CATALOG_URL
		self.baseTopicS=f"{baseTopic}{patient}/actuators"
		self.__message={
			'patientID':self.patient, 
			'bn':'',
			'e':
				[
					{'n':'','value':'', 'timestamp':'','u':''},
					]
			}
		r=requests.get(self.CATALOG_URL+f'/broker') 
		self.broker = r.json()["IPaddress"]
		self.port = r.json()["port"]
		self.client=MyMQTT(self.clientID,self.broker,self.port,self)

		self.previous_hr=60 #inizilizzazione per la heart rate "rest"
		self.status_airC=0 #per airConditionair_1 0 spento, 1 acceso
		self.status_light=0 #for the lights

	def RESTCommunication(self,filename):
		self.connected_devices = json.load(open(filename))
		
		self.t={}
		#t model:
		#t = {
		# "Light": "iSupport/1/actuators/Light",
		# "Air": "iSupport/1/actuators/Air"
		# }
		for item in self.connected_devices["Actuators"]:
			for SD in item["servicesDetails"]: #item["servicesDetails"] è una lista
				if SD["serviceType"]=='MQTT':
					for topic in SD["topic"]:
						key = topic.split('/')[3]
						value = topic
						self.t[key]=value

		for device in self.connected_devices["Sensors"]+self.connected_devices["Actuators"]:
			r=requests.get(self.CATALOG_URL+f'/deviceID/{device["deviceID"]}') #retrive the device 
			if r.text=='':
				#new Registration
				requests.post(self.CATALOG_URL+f'/device',json=device)
			else:
				#updating Devices
				requests.put(self.CATALOG_URL+f'/device',json=device)

	def MQTTinfoRequest(self):
		r=requests.get(self.CATALOG_URL+f'/broker') 
		#if self.broker and self.port: # se non esistono broker e port questa linea dà errore
		if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #if the broker is changed
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client.stop()
			self.client=MyMQTT(self.clientID,self.broker,self.port,self)
			self.start()
			
		# else:
		# 	self.broker = r.json()["IPandress"]
		# 	self.port = r.json()["port"]
		# 	self.client=MyMQTT(self.clientID,self.broker,self.port,self)
		# 	self.start()

		
	#Solo per noi per aggiungere i devices alla lista dei connessi
	# def insertNewDevice(self,newDevice):
	# 	#insert a new device (json data type) into the catalog exploiting REST Web Services
	# 	CONNECTED_DEVICES[].append(json.loads(newDevice))
	# 	#print(CONNECTED_DEVICES)
	
	def start(self):
		self.client.start()
		#for topic in self.t["topic"]:
		for topic in self.t.values():
			self.client.mySubscribe(topic)

	def stop(self):
		self.client.stop()

	def publish(self,range_hr,flag_temp,flag_motion): #range_hr è per resting/danger/sport per HR, flag_temp per generare temp e hum fuori dai range "normali" (o normale, 1 altrimenti)
		#flag_motion=1/0 on(pff)
		for d in self.connected_devices["Sensors"]:
		
			print(f'Message structure: {self.__message}')
			print("###############  new Device #############################")
		
		
			topic=d["servicesDetails"][0]["topic"]
			if d["measureType"]==["Humidity","Temperature"]:
				msg=dict(self.__message)
				if self.status_airC==1: #airConditionair attivo
					#controllare per range temporale (estate/inverno)
					month = datetime.now().month #è un intero
					if 10<=month<=12 or 1<=month<=3: #winter
						a_temp=random.uniform(19,21)
						a_hum=random.uniform(40,42)
					else: #summer
						a_temp=random.uniform(24,26)
						a_hum=random.uniform(50,52)

				elif self.status_airC==0: #airConditionair spento
					if flag_temp==0: #temperatura nel range corretto
						a_temp=random.uniform(18,26)
						if 18<=a_temp<=23:
							a_hum=random.uniform(40,50)					
						elif 24<=a_temp<=26:
							a_hum=random.uniform(50,60)	
					elif flag_temp==1: #temperatura fuori range
						a=np.arange(0,17,0.2)
						b=np.arange(27,41)
						c=[float(i) for i in list(a)+list(b)]
						a_temp=choice(c)
						if a_temp<=17:
							a_hum=random.uniform(40,50)					
						elif a_temp>=27:
							a_hum=random.uniform(50,60)
				
				msg['bn']=d["deviceID"]
				msg['e']=[{'n':'Temperature','value':a_temp,'timestamp':str(datetime.now()),'u':'C'},{'n':'Humidity','value':a_hum,'timestamp':str(datetime.now()),'u':'%'}]

			elif d["measureType"]==['HeartRate']: 
				msg=dict(self.__message)
				msg['bn']=d["deviceID"]
				msg['e'][0]['n']='HeartRate'
				print(range_hr)
				if range_hr=='r': #rest
					shape, scale = 0., 1. # mean=4, std=2*sqrt(2)
					a= self.previous_hr+2*np.random.logistic(shape, scale) # genera un solo valore  
					print(a)
					self.previous_hr=a
				elif range_hr=='d' or range_hr=='s': #danger o sport
					shape, scale = 5., 10.  # mean=4, std=2*sqrt(2)
					a = np.random.gamma(shape, scale)+110
				msg['e'][0]['value']=a
				msg['e'][0]['timestamp']=str(datetime.now())
				msg['e'][0]['u']='bpm'
				
			elif d["measureType"]==['Motion']:
				msg=dict(self.__message)
				msg['bn']=d["deviceID"]
				msg['e'][0]['n']='Motion'
				msg['e'][0]['value']=flag_motion
				msg['e'][0]['timestamp']=str(datetime.now())
				msg['e'][0]['u']='bool'

			elif d["measureType"]==["Accelerometer"]: 
				msg=dict(self.__message)
				if range_hr=='r' or range_hr=='d':
					n=random.randint(5,len(self.linesREST))		
					m=self.linesREST[n].split(',')
					float_number=[float(number) for number in m]
					a=float_number[4]
				
				elif range_hr=='s':
					n=random.randint(5,len(self.linesSPORT))		
					m=self.linesSPORT[n].split(',')
					float_number=[float(number) for number in m]
					a=float_number[4] #the absolute value of the accelerometer 3-axial measurements
				
				msg['bn']=d["deviceID"]
				msg['e'][0]['n']='Accelerometer'
				msg['e'][0]['value']=a
				msg['e'][0]['timestamp']=str(datetime.now())
				msg['e'][0]['u']='m/s'
				
				
			self.client.myPublish(topic[0],msg)
			time.sleep(15)

	def notify(self,topic,payload):
		#lights, airConditionair
		payload=json.loads(payload)		
		
		if topic.split('/')[3] == 'Light':
			#relays command (Lights)
			self.status_light=payload["e"][0]["value"]
		elif topic.split('/')[3] == 'Air':
			self.status_airC==payload["AirConditionairStatus"]			

if __name__=="__main__":
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	patientID = conf["DeviceConnector"]["patientID"]
	clientID='DeviceConnector'+str(patientID)
	fp.close()
	

	fp = open("REST.txt") 
	linesREST=fp.readlines()
	fp.close()

	fp = open("SPORT.txt") 
	linesSPORT=fp.readlines()
	fp.close()

	dc=DeviceConnector(CATALOG_URL,clientID,patientID,bT,linesREST,linesSPORT)
	dc.RESTCommunication(sys.argv[2])
	dc.start()
	#dc.MQTTinfoRequest()
	#first step: connection and registration    
	i=1
	while True:
		#On off del motion valutare cosa mettere (più presenza/assenza)
		command=input('Insert the command:\n1.Set the acivity status of the patient:\n\ta."r" for rest activity\n\tb."s" for sport activity\n\tc."d" for a panik attack\n2.Set the temperature status:\n\t1=In range value\n\t0=Out of range value\n3.Set the motion sensor:\n\t1=On\n\t0=Off\n')
		command=command.split(',')
		# dc.RESTCommunication(sys.argv[2])
		try:
			while True:
				dc.publish(command[0],int(command[1]),command[2]) #0: range heart rate, 1: temperatura(0/1=dentro/fuori range), 2: motion sensor (1/0=on/off) 
				if i==2: #every 120s
					dc.RESTCommunication(sys.argv[2])
					dc.MQTTinfoRequest()
					i=0
				# time.sleep(45)  
				i=i+1
		except KeyboardInterrupt: #CRTL+C per cambiare stato 
			continue
	dc.stop()
