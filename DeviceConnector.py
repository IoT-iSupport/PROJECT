import json
from datetime import datetime
from myMQTT import *
import random
import requests
import numpy as np
from random import choice
import sys

class DeviceConnector():
	def __init__(self,CATALOG_URL,clientID,linesREST,linesSPORT):
		self.linesREST = linesREST
		self.linesSPORT = linesSPORT
		self.clientID = clientID
		self.CATALOG_URL = CATALOG_URL
		
		#initialisation for broker and port
		self.broker=''
		self.port=0
		#message structure
		self.__message={
			'bn':'',
			'e':
				[
					{'n':'','value':'', 'timestamp':'','u':''},
					]
			}
		self.status_airC=0 #for airConditionair_1 0 off, 1 on
		self.status_light=0 #for the lights 0 off, 1 on

	def RESTCommunication(self,filename):
		fp=open(filename)
		self.connected_devices = json.load(fp)
		fp.close()

		self.t={}
		#t structure:
		#t = {
		# "Light": "iSupport/1/actuators/Light",
		# "Air": "iSupport/1/actuators/Air"
		# }
		for item in self.connected_devices["Actuators"]: #append topic
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
				#print(f'Registered DeviceID: {device["deviceID"]}')
			else:
				#refresh Devices reistration
				requests.put(self.CATALOG_URL+f'/device',json=device)
				#print(f'Updated registration of DeviceID: {device["deviceID"]}')

	def MQTTinfoRequest(self):
		r=requests.get(self.CATALOG_URL+f'/broker') #retrieve broker/port 
		if self.broker and self.port: #if broker and port already exist...
			if not self.broker == r.json()["IPaddress"] or not self.port == r.json()["port"]: #check if the broker is changed...
				self.broker = r.json()["IPaddress"] #... update broker and port
				self.port = r.json()["port"] 
				self.client.stop()  #stop the previous client and 
				self.client=MyMQTT(self.clientID,self.broker,self.port,self) #create and start new client
				self.start()
			
		else: #create and start new client
			self.broker = r.json()["IPaddress"]
			self.port = r.json()["port"]
			self.client=MyMQTT(self.clientID,self.broker,self.port,self)
			self.start()

	def start(self): #start client and subsribe to topics
		self.client.start()
		for topic in self.t.values():
			self.client.mySubscribe(topic)

	def stop(self):
		self.client.stop()

	def publish(self,range_hr,flag_temp,flag_motion): 
		#range_hr= is a letter r(=rest)/d(=danger)/s(=sport) for HR and accelerometer measurements
		#flag_temp = is a boolean for temp and hum out of comfort-home-status, ranges 1 = in range value, 0=out of range value
		#flag_motion=is a boolean that stands for 1= Presence or 0=Not presence
		
		for d in self.connected_devices["Sensors"]:
			print('\n')	
			topic=d["servicesDetails"][0]["topic"]
					  
			#Temperature and Humidity
			if d["measureType"]==["Humidity","Temperature"]:
				msg=dict(self.__message)
				if self.status_airC==1: #airConditionair on
					#check current season
					month = datetime.now().month #it is an integer
					if 10<=month<=12 or 1<=month<=3: #winter
						a_temp=random.uniform(19,21)
						a_hum=random.uniform(40,42)
					else: #summer
						a_temp=random.uniform(24,26)
						a_hum=random.uniform(50,52)

				elif self.status_airC==0: #airConditionair system off
					if flag_temp==1: #temperature in range
						a_temp=random.uniform(18,26)
						if 18<=a_temp<23:
							a_hum=random.uniform(40,50)					
						elif 23<=a_temp<=26:
							a_hum=random.uniform(50,60)	
					elif flag_temp==0: #temperature out of range
						a=np.arange(0,17,0.2) #temperature lower than 17??C
						b=np.arange(27,41)    #temperature higher than 27??C
						c=[float(i) for i in list(a)+list(b)]
						a_temp=choice(c) 
						if a_temp<=17:
							a_hum=random.uniform(40,50)					
						elif a_temp>=27:
							a_hum=random.uniform(50,60)
				
				msg['bn']=d["deviceID"]
				msg['e']=[{'n':'Temperature','value':a_temp,'timestamp':str(datetime.now()),'u':'C'},{'n':'Humidity','value':a_hum,'timestamp':str(datetime.now()),'u':'%'}]

			#Accelerometer and Heart Rate
			elif d["measureType"]==['HeartRate',"Accelerometer"]: 
				msg=dict(self.__message)
				msg['bn']=d["deviceID"]
				
				#Heart Rate
				if range_hr=='r': #rest
					loc, scale = 60, 1
					a= np.random.logistic(loc, scale) 
				elif range_hr=='d' or range_hr=='s': #danger/panic attack o sport
					shape, scale = 5., 10. 
					a = np.random.gamma(shape, scale)+110
				
				#Accelerometer
				if range_hr=='r' or range_hr=='d': #rest or danger/panic attack
					n=random.randint(4,len(self.linesREST)-1)		
					m=self.linesREST[n].split(',')
					float_number=[float(number) for number in m]
					b=float_number[4]
				
				elif range_hr=='s': #sport
					n=random.randint(4,len(self.linesSPORT)-1)		
					m=self.linesSPORT[n].split(',')
					float_number=[float(number) for number in m]
					b=float_number[4] #the absolute value of the accelerometer 3-axial measurements
				
				msg['e']=[{'n':'HeartRate','value':a,'timestamp':str(datetime.now()),'u':'bpm'},{'n':'Accelerometer','value':abs(b),'timestamp':str(datetime.now()),'u':'m/s2'}]


			#Motion	
			elif d["measureType"]==['Motion']:
				msg=dict(self.__message)
				msg['bn']=d["deviceID"]
				msg['e'][0]['n']='Motion'
				msg['e'][0]['value']=flag_motion
				msg['e'][0]['timestamp']=str(datetime.now())
				msg['e'][0]['u']='bool'				
				
			self.client.myPublish(topic[0],msg)
			time.sleep(15)

	def notify(self,topic,payload): #For receiving actuations command for lights and airConditionair system
		payload=json.loads(payload)		
		
		if topic.split('/')[3] == 'Light':
			#relays command (Lights)
			self.status_light=payload["e"][0]["value"]
			#print(f'\nlight status of light_{topic.split("/")[1]} set to {self.status_light}')
		elif topic.split('/')[3] == 'Air':
			self.status_airC==payload["AirConditionairStatus"]			

if __name__=="__main__":
	#sys.argv[1] is Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	CATALOG_URL = conf["Catalog_url"]
	fp.close()
	
	#txt files with accelerometer measurements
	fp = open("REST.txt") 
	linesREST=fp.readlines()
	fp.close()

	fp = open("SPORT.txt") 
	linesSPORT=fp.readlines()
	fp.close()

	#sys.argv[2] is  CONNECTTED_DEVICE.JSON 
	fp = open(sys.argv[2])
	dev = json.load(fp)
	patientID = dev["patientID"]
	clientID='DeviceConnector'+str(patientID)
	fp.close()

	dc=DeviceConnector(CATALOG_URL,clientID,linesREST,linesSPORT)
	
	dc.RESTCommunication(sys.argv[2])
	dc.MQTTinfoRequest()
	   
	i=1
	while True:
		command=input('Insert the command:\n1.Set the acivity status of the patient:\n\ta."r" for rest activity\n\tb."s" for sport activity\n\tc."d" for a panik attack\n2.Set the temperature status:\n\t1=In range value\n\t0=Out of range value\n3.Set the motion sensor:\n\t1=Presence\n\t0=Unpresence\n')
		command=command.split(',')
		dc.RESTCommunication(sys.argv[2])
		try:
			while True:
				dc.publish(command[0],int(command[1]),command[2]) #0: heart rate range, 1: temperature(1/0=in/out of range), 2: motion sensor (1/0=on/off) 
				if i==2: #about every 120s register devices or refresh registration and retrieve broker/port
					try:
						dc.RESTCommunication(sys.argv[2])
						dc.MQTTinfoRequest()
					except:
						print('Catalog Communication failed')
					i=0 
				i=i+1
		except KeyboardInterrupt: #CRTL+C for changing status 
			continue
	dc.stop()

