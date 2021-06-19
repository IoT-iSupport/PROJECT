import requests
import json
import sys 

class ManageUser():
    def __init__(self,catalog_url):
        self.catalog_url=catalog_url

    def Add(self):
        body = {}
        r = requests.get(self.catalog_url+'/patients')
        patients = r.json()
        ids = []
        for p in patients:
            ids.append(int(p['patientID']))
        if not ids: #if no patient is registered...
            id =1
        else:
            id = max(ids)+1 #new patient ID
        
        print('ADD NEW PATIENT:')
        body['patientID'] = str(id)
        body['patientName'] = input('Insert the name:\n')
        body['patientSurname'] = input('Insert the surname:\n')
        body['LightsSchedule'] = input('Insert the light schedule in the format HH:MM-H:MM:\n')
        body['connectedDevices'] = self.devices_file(id) #create device connected with patient
        print('ThingSpeak Specification:')
        body['thingspeakInfo'] = {'apikeys':input('Insert the ThingSpeak APIkeys separated by a comma:').split(','),'channel':input('Insert the number of the channel:')}
        body["telegramIDs"]=[]
        r = requests.post(self.catalog_url+'/patient',json = body) #post request to register new patient
        print(f'\nUser correcly registered with id {id}\n')

    def Update(self,id):
        r = requests.get(self.catalog_url+'/patientID/{}'.format(id))
        if r.text=='':
            res={"output":'Patient not registered yet'}
            return res
        else:
            patient = r.json()
            print('Current information:')
            for x,y in patient.items():
                print(f"\t{x}: {y}")
            body={}
            body["patientID"]=str(id)
            body["patientName"]=input('Update the name:\n')
            body["patientSurname"]=input('Update the surname:\n')
            body["LightsSchedule"]=input('Update the light schedule in the format HH:MM-H:MM:\n')
            body['thingspeakInfo'] = {'apikeys':input('Update the ThingSpeak APIkeys separated by a comma:').split(','),'channel':input('Update the number of the channel:')}
            r = requests.put(self.catalog_url+'/patient',json = body) #put request to update information
            res={"output":'Information Updated'}
            return res
        
                

    def devices_file(self,id):
        r = requests.get(self.catalog_url+'/devices')
        DEV = r.json()
        ids = []
        for dev in DEV:
            ids.append(int(dev['deviceID']))
        if not ids:
            m = 0
        else:
            m = max(ids)
        body = {
        "patientID": id,
        "Sensors":[{
                "deviceName":f"smartwatch_{id}",
                "deviceID":f"{m+1}",
                "measureType":[
                    "HeartRate","Accelerometer"
                ],
                "availableServices":[
                    "MQTT"
                ],
                "servicesDetails":[{
                        "serviceType":"MQTT",
                        "topic":[f"iSupport/{id}/sensors/Body"]
                    }]},
                
                {
                "deviceName":f"mot_{id}",
                "deviceID":f"{m+2}",
                "measureType":["Motion"],
                "availableServices":["MQTT"],
                "servicesDetails":[{
                    "serviceType":"MQTT",
                    "topic":[f"iSupport/{id}/sensors/Motion"]
                }]
                },
                {
                "deviceName":f"airConditionair_{id}",
                "deviceID":f"{m+3}",
                "measureType":["Humidity","Temperature"],
                "availableServices":["MQTT"],
                "servicesDetails":[{
                    "serviceType":"MQTT",
                    "topic":[f"iSupport/{id}/sensors/Air"]
                }]
            }],
        "Actuators":[
            {
                    "deviceName":f"light_{id}",
                    "deviceID":f"{m+4}",
                    "availableServices":["MQTT"],
                    "servicesDetails":[{
                        "serviceType":"MQTT",
                        "topic":[f"iSupport/{id}/actuators/Light"]
                    }]
            },{
                    "deviceName":f"airConditionair_{id}",
                    "deviceID":f"{m+5}",
                    "availableServices":["MQTT"],
                    "servicesDetails":[{
                        "serviceType":"MQTT",
                        "topic":[f"iSupport/{id}/actuators/Air"]
                    }]
                }
        ]}
        #CONNECTED_DEVICES.json with devices associated with the patient
        fp = open(f'CONNECTED_DEVICES{id}.json','w')
        json.dump(body,fp,indent=4)
        fp.close()
        
        connD = []
        for sensor in body['Sensors']:
            device = {"measure": sensor['measureType'],"deviceID": sensor['deviceID']}
            connD.append(device)
        for actuator in body['Actuators']:
            device = {"measure": actuator['deviceName'].split('_')[0] + ' actuator',"deviceID": actuator['deviceID']}
            connD.append(device)
        return connD


if __name__ == "__main__":
    helpMessage="Press 'add' to add a new user\nPress 'update' to update information of a user already inserted\nPress 'quit' to save end exit"
    fp = open(sys.argv[1])
    conf = json.load(fp)
    fp.close()
    catalog_url = conf["Catalog_url"]
    c=ManageUser(catalog_url)
    while True:
        print(helpMessage)
        command=input()
        if command=='add':
            c.Add()
        elif command=='update':
            id=input('Insert patientID of the user you want to update:\n')
            output=c.Update(id)
            print(f'{output["output"]}\n')
        elif command=='quit':
            break
        else:
            print('Wrong command\n')