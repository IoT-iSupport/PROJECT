import paho.mqtt.client as PahoMQTT #mosquito
import json
import time
#general propouse client
class MyMQTT:
    def __init__(self, clientID, broker, port, notifier=None):
        self.broker = broker 
        self.port = port 
        self.notifier = notifier 
        self.clientID = clientID 
        self._topic =""
        self._isSubscriber =False
        # create an instance of paho.mqtt.client
        self._paho_mqtt = PahoMQTT.Client(clientID,False) #client id and false for durable subscription
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect #established a connection
        #when my mqtt client is connected, execute myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived
    
    def myOnConnect(self, paho_mqtt, userdata, flags, rc):
        print("Connected to %s with result code: %d"% (self.broker, rc)) # 0 means connected
    
    def myOnMessageReceived(self, paho_mqtt , userdata, msg):
        # A new message is received
        self.notifier.notify (msg.topic, msg.payload)

    def myPublish(self, topic, msg):
        print("publishing '%s' with topic '%s'"% (msg, topic))
        # publish a message with a certain topic
        self._paho_mqtt.publish(topic,json.dumps(msg),2) 
        #2 is the best to use (QoS)
    
    def mySubscribe(self, topic):
        print("subscribing to %s" % (topic))
        # subscribe for a topic
        self._paho_mqtt.subscribe(topic,2)
        self._isSubscriber =True
        self._topic = topic
    def unsubscribe(self):
        if (self._isSubscriber): 
            self._paho_mqtt.unsubscribe(self._topic)

    def start(self):
        #manage connection to broker
        self._paho_mqtt.connect(self.broker , self.port) 
        
        self._paho_mqtt.loop_start()
    
    
    def stop(self):
        if (self._isSubscriber):
            # remember to unsuscribe if it is working also as subscriber
            self._paho_mqtt.unsubscribe(self._topic) 
            self._paho_mqtt.loop_stop() 
            self._paho_mqtt.disconnect()
          
