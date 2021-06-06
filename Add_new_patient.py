import requests
import json
import sys 

def main():
	#sys.argv[1] is Configuration_file.json
	fp = open(sys.argv[1])
	conf = json.load(fp)
	fp.close()

	catalog_url = conf["Catalog_url"]

	body = {}
	r = requests.get(catalog_url+'/patients')
	patients = r.json()
	ids = []
	for p in patients:
		ids.append(int(p['patientID']))
	if not ids: #if no patient is registered...
		id =0
	else:
		id = max(ids)+1 #new patient ID
	
	print('ADD NEW PATIENT:')
	body['patientID'] = id
	body['connectedDevices'] = devices_file(id,catalog_url) #create device connected with patient
	body['patientName'] = input('Insert the name:\n')
	body['patientSurname'] = input('Insert the surname:\n')
	body['LightsSchedule'] = input('Insert the light schedule in the format HH:MM-H:MM:\n')
	print('ThingSpeak Specification:')
	body['thingspeakInfo'] = {'apikeys':input('Insert the ThingSpeak APIkeys separated by a comma:').split(','),'channel':input('Insert the number of the channel:')}
	body["telegramIDs"]=[]
	print(body)
	r = requests.post(catalog_url+'/patient',json = body) #post request to register new patient

def devices_file(id,catalog_url):
	r = requests.get(catalog_url+'/devices')
	DEV = r.json()
	print(DEV)
	ids = []
	for dev in DEV:
		ids.append(int(dev['deviceID']))
	if not ids:
		m = 0
	else:
		m = max(ids)
	body = {
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
	print(connD)
	return connD

if __name__ == "__main__":
	main()