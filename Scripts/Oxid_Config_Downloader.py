#This Script downloads all of your device configs from Oxidized.

from Libs.LibreNMSAPIClient import LibreNMSAPIClient
import os
libreapi =  LibreNMSAPIClient()

output_dir="configs/"  #Output Directory



if not os.path.exists(output_dir): 
    os.makedirs(output_dir)

device_hostname_sysname={}
for device in libreapi.list_devices():
    device_hostname_sysname[device['hostname']]=device['sysName']

for dev in libreapi.list_oxidized(): 
    dev_config=libreapi.i_get_oxidized_config(dev['hostname']) #Get Config from Oxidized
    if(len(dev_config)!=0 and dev_config != "node not found"): #Verify Valid Config
        f=open(output_dir + device_hostname_sysname[dev['hostname']] + ".cfg","w")
        f.write(dev_config)
        f.close()
