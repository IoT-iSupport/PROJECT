#  iSUPPORT PLATFORM (programming for IoT application project)


Link **DEMO**: [https://youtu.be/iXHYLhUb1us](https://youtu.be/iXHYLhUb1us)

Link **PROMO**: [https://youtu.be/xe4MlNTb9Qs](https://youtu.be/xe4MlNTb9Qs)

_______________________________________________________________________

The Catalog needs a second parameter from the command line (Catalog.json)

The name of the file where the information about Catalog IP address and other information for each microcervices are stored must be passed from command line. 
(Configuration_file.json in this folder).
The device connector needs a second parameter from the command line, which is the name of the file that contains the information about the devices connected to the
patient.(*CONNECTED_DEVICE.json* in this folder is linked to the patient with the id = 1).

**NOTE**: In Catalog.json a patient (with ID 1) is already inserted but it is possible to add more patients using the script *Add_patient.py*. This script also creates a json
file (CONNECTED_DEVICEid.json) with the information about the devices connected to the registered patient. Once the new patient is inserted is necessary to start the
DeviceConnector.py with the 2 command line argument: *Configuration_file.json* and *CONNECTED_DEVICEid.json* where ID is the ID of the newly registered user
To test the platform with 2 patients, this second thingspeak channel has already been created:
- thingspeakInfo: ZQ2AJZABDSC4MXXG, SV1HOET58CE7225M; 
- channel: 1342741

_______________________________________________________________________

The Device connector can simulate different situation: it can be shifted from a normal status to a dangerous one (panic attack).
**It is raccomanded** for the Panic attack simulation to run before a rest status or a sport one, and after 10 minutes, shift to the dangerous status, 
in order to allow the Patient control to detect the changes.

_______________________________________________________________________

For the telegram bot, first of all, you have to start the conversation with the command */start* that allows the storage of your chatID to a specific patient.

_______________________________________________________________________

For the NODE-RED flow see the file in this folder. Palette used:
- Digital Display: *node-red-contib-ui-digital-display*
- Dashboard: *node-red-dashboard*
