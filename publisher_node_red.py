from myMQTT import *
import random

#script per provare node-red

client=MyMQTT("pub_node_resd","test.mosquitto.org",1883)
client.start() 

message={"patientID":1,
        "average heart rate":{
                "min_value":[1, 2, 3],
                "max_value":[10, 11, 12],
                "mean_value":[4, 5, 6]
        },
    "activity status":[30, 40, 30],
    "bedroomMotion":30   
}
message1={"patientID":1,
            "Panik Attack":2
            }
i=1
while True:
    if i%5==0:
        message1["Panik Attack"]=i+random.randint(1,10)
        client.myPublish("iSupport/1/nodered",message1)
        i=1
    else:
        message["average heart rate"]["mean_value"]=[i,i*2,i*3]
        message["activity status"]=[i*2,i,i*3]
        message["bedroomMotion"]=i+4
        client.myPublish("iSupport/1/nodered",message)
    #client.myPublish("iSupport/1/nodered",message1)
    time.sleep(5)
    i+=1

#codice node-red python function:
# output1={}
# output2={}
# output3={}
# output4={}
# if "average heart rate" in msg["payload"]:
#     output1={"topic":"average heart rate","payload":[{
#     "series": [ "X", "Y", "Z"],
#     "data": [msg["payload"]["average heart rate"]["mean_value"][0],msg["payload"]["average heart rate"]["mean_value"][1],msg["payload"]["average heart rate"]["mean_value"][2]],
#     "labels": [ "1","2", "3" ]
#     }]}
    
#     output2={"topic":"activity status","payload":[{
#     "series": [ "X", "Y", "Z"],
#     "data": [msg["payload"]["activity status"][0],msg["payload"]["activity status"][1],msg["payload"]["activity status"][2]],
#     "labels": [ "1","2", "3" ]
#     }]}
    
#     output3={"topic":"bedroomMotion","payload":[{
#     "series": [ "X" ],
#     "data": [msg["payload"]["bedroomMotion"]],
#     "labels": [ "1" ]
#     }]}
    
# elif "Panik Attack" in msg["payload"]:
#     output4={"topic":"Panik Attack","payload":[{
#     "series": [ "X" ],
#     "data": [msg["payload"]["Panik Attack"]],
#     "labels": [ "1" ]
#     }]}
# #"data": [msg["payload"]["average heart rate"]["min_value"] ],
# return output1,output2,output3,output4