from myMQTT import *
test=MyMQTT("testIoTBot",'test.mosquitto.org',1883,None)
test.start()
for i in range(5):
    message={"alert":"is having a Panik attack","action":"check the situation"}
    #topic="iSupport/"+str(i)+"/telegram"
    topic="iSupport/"+str(i)+"/telegram"
    test.myPublish(topic,message)
    time.sleep(3)