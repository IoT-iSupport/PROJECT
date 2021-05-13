import json
from datetime import datetime
from MyMQTT import *
import random
import threading
import requests
import numpy as np
from random import choice
import sys

# CATALOG_URL='http://127.0.0.1:8080'
# patient=1

class DeviceConnector():
	def __init__(self,CATALOG_URL,clientID,patient,baseTopic,linesREST,linesSPORT):
		self.linesREST = linesREST
		self.linesSPORT = linesSPORT
		self.patient = patient
		self.clientID = clientID
		self.CATALOG_URL = CATALOG_URL
		self.baseTopicS=f"{baseTopic}{patient}/actuators"
		
		#initialisation for broker and port
		self.broker=''
		self.port=0
		
		self.__message={
			'patientID':self.patient, 
			'bn':'',
			'e':
				[
					{'n':'','value':'', 'timestamp':'','u':''},
					]
			}
		
		self.previous_hr=60 #initialisation for "rest" heart rate 
		self.status_airC=0 #initialisation for airConditionair_1 (0 off, 1 on)
		self.status_light=0 #initialisation for the lights (0 off, 1 on)

	def RESTCommunication(self,filename): # devices registration
		self.connected_devices = json.load(open(filename))
		
		#actuators topics
		self.t={}
		#t model:
		#t = {
		# "Light": "iSupport/1/actuators/Light",
		# "Air": "iSupport/1/actuators/Air"
		# }
		for item in self.connected_devices["Actuators"]:
			for SD in item["servicesDetails"]:
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
				#refresh registration, updating Devices
				requests.put(self.CATALOG_URL+f'/device',json=device)

	def MQTTinfoRequest(self): #retrieve broker/port 
		r=requests.get(self.CATALOG_URL+f'/broker') 
		if self.broker and self.port: #if broker and port already exist...
			print('if MQTTinfoRequest')
			if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #check if the broker is changed...
				self.broker = r.json()["IPaddress"] #... update broker and port
				self.port = r.json()["port"]
				print(self.port)
				self.client.stop() #stop the previous client
				self.client=MyMQTT(self.clientID,self.broker,self.port,self) #creat and start a new client
				self.start()
			
		else: #create and start new client
			print('else MQTTinfoRequest')
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client=MyMQTT(self.clientID,self.broker,self.port,self)
			self.start()

		
	#Solo per noi per aggiungere i devices alla lista dei connessi
	# def insertNewDevice(self,newDevice):
	# 	#insert a new device (json data type) into the catalog exploiting REST Web Services
	# 	self.connected_devices[].append(json.loads(newDevice))
	# 	#print(self.connected_devices)
	
	def start(self): #start the client and subscribe to actuartors topics in order to receive messages from LightShift and HomeSystemControl
		self.client.start()
		for topic in self.t.values():
			self.client.mySubscribe(topic)

	def stop(self):
		self.client.stop()

	def publish(self,range_hr,flag_temp,flag_motion): #range_hr for HR rest/danger/sport, flag_temp for generate temp e hum out of range (1= out of range), flag_motion=1/0 on/off
		for d in self.connected_devices["Sensors"]:
		
			print(f'Message structure: {self.__message}')
			print("###############  new Device #############################")
		
		
			topic=d["servicesDetails"][0]["topic"]
			#Temperature and Humidity Sensor
			if d["measureType"]==["Humidity","Temperature"]:
				msg=dict(self.__message)
				if self.status_airC==1: #airConditionair on
					#check the current month (summer/winter)
					month = datetime.now().month 
					if 10<=month<=12 or 1<=month<=3: #winter
						a_temp=random.uniform(19,21)
						a_hum=random.uniform(40,42)
					else: #summer
						a_temp=random.uniform(24,26)
						a_hum=random.uniform(50,52)

				elif self.status_airC==0: #airConditionair off
					if flag_temp==0: #temperature in correct range
						a_temp=random.uniform(18,26)
						if 18<=a_temp<=23:
							a_hum=random.uniform(40,50)					
						elif 24<=a_temp<=26:
							a_hum=random.uniform(50,60)	
					elif flag_temp==1: #temperatura out of range
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
			
			#HeartRate Sensor
			elif d["measureType"]==['HeartRate']: 
				msg=dict(self.__message)
				msg['bn']=d["deviceID"]
				msg['e'][0]['n']='HeartRate'
				print(range_hr)
				if range_hr=='r': #rest
					shape, scale = 0., 1.
					a= self.previous_hr+2*np.random.logistic(shape, scale) 
					print(a)
					self.previous_hr=a
				elif range_hr=='d' or range_hr=='s': #danger or sport
					shape, scale = 5., 10.  # mean=4, std=2*sqrt(2)
					a = np.random.gamma(shape, scale)+110
				msg['e'][0]['value']=a
				msg['e'][0]['timestamp']=str(datetime.now())
				msg['e'][0]['u']='bpm'
				
			#Motin Sensor
			elif d["measureType"]==['Motion']:
				msg=dict(self.__message)
				msg['bn']=d["deviceID"]
				msg['e'][0]['n']='Motion'
				msg['e'][0]['value']=flag_motion
				msg['e'][0]['timestamp']=str(datetime.now())
				msg['e'][0]['u']='bool'
			
			#Acceleroemter
			elif d["measureType"]==["Accelerometer"]: 
				msg=dict(self.__message)
				if range_hr=='r' or range_hr=='d': #rest or danger
					n=random.randint(5,len(self.linesREST))	#generate a random number and read the correspondig line in REST.txt	
					m=self.linesREST[n].split(',')
					float_number=[float(number) for number in m]
					a=float_number[4] #the absolute value of the accelerometer 3-axial measurements
				
				elif range_hr=='s': #sport
					n=random.randint(5,len(self.linesSPORT)) #generate a random number and read the correspondig line in SPORT.txt		
					m=self.linesSPORT[n].split(',')
					float_number=[float(number) for number in m]
					a=float_number[4] #the absolute value of the accelerometer 3-axial measurements
				
				msg['bn']=d["deviceID"]
				msg['e'][0]['n']='Accelerometer'
				msg['e'][0]['value']=a
				msg['e'][0]['timestamp']=str(datetime.now())
				msg['e'][0]['u']='m/s'
				
				
			self.client.myPublish(topic[0],msg)
			time.sleep(15) #Publish every 15s in order to save data on ThingSpeak

	def notify(self,topic,payload): # receive actuation command for lights, airConditionair
		payload=json.loads(payload)		
		
		if topic.split('/')[3] == 'Light':
			#relays command (Lights)
			self.status_light=payload["e"][0]["value"]
		elif topic.split('/')[3] == 'Air':
			self.status_airC==payload["AirConditionairStatus"]			

if __name__=="__main__":
	# command line argument in position 1 is the Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	bT = conf["baseTopic"] 
	patientID = conf['DeviceConnector']["patientID"]
	clientID='DeviceConnector'+str(patientID)
	fp.close()
	
	# open and read files with accelerometer measurements
	fp = open("REST.txt") 
	linesREST=fp.readlines()
	fp.close()

	fp = open("SPORT.txt") 
	linesSPORT=fp.readlines()
	fp.close()
	
	dc=DeviceConnector(CATALOG_URL,clientID,patientID,bT,linesREST,linesSPORT)
				       
	#command line argument in position 2 is the CONNECTED_DEVICE.json. Registration of the sensors/actuators			       
	dc.RESTCommunication(sys.argv[2])
	#retreive broker/port information, create and the client
	dc.MQTTinfoRequest()
	 
	i=1
	while True:
		#On off del motion valutare cosa mettere (più presenza/assenza)
		command=input('Insert the command:\n1.Set the acivity status of the patient:\n\ta."r" for rest activity\n\tb."s" for sport activity\n\tc."d" for a panik attack\n2.Set the temperature status:\n\t1=In range value\n\t0=Out of range value\n3.Set the motion sensor:\n\t1=On\n\t0=Off\n')
		command=command.split(',')
		dc.RESTCommunication(sys.argv[2])
		try:
			while True:
				dc.publish(command[0],int(command[1]),command[2]) #0: range heart rate, 1: temperatura(0/1=dentro/fuori range), 2: motion sensor (1/0=on/off) 
				if i==2: #every 120s refresh the devices registration and retrieve broker/port
					dc.RESTCommunication(sys.argv[2])
					dc.MQTTinfoRequest()
					i=0
				# time.sleep(45)  
				i=i+1
		except KeyboardInterrupt: #CRTL+C per cambiare stato 
			continue
	dc.stop()
