# ioT PROJECT
The name of the file where the information about broker, port, etc. is stored must be passed from command line. 
(Configuration_file.json in this folder).

The device connector needs a second parameter from the command line,
which is the name of the file that contains the information about the devices connected to the patient. 
(CONNECTED_DEVICE.json in this folder)

The Device connector can simulate different situation: it can be shifted from a normal status to a dangerous one.
It is raccomanded, for the Panik attack simulation to run before a rest status or a sport one, and after 10 minutes, shift to the dangerous status, 
in order to allow the Patient control to detect the changes.
