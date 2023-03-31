import pandas as pd
from pybatfish.client.session import Session
from pybatfish.datamodel import *
from pybatfish.datamodel.answer import *
from pybatfish.datamodel.flow import *

from Libs.LibreNMSAPIClient import LibreNMSAPIClient
import re
import tempfile
import os
libreapi=LibreNMSAPIClient()
      

def download_config(tempdir,os,sysdescr_exclude_regex=""):
    for device in libreapi.list_devices():
        if device['os'] == os and (sysdescr_exclude_regex == "" or not re.search(sysdescr_exclude_regex,device['sysDescr'])) and not ('attribs' in device and 'override_Oxidized_disable' in device['attribs'] and device['attribs']['override_Oxidized_disable'] == 'true'):
            with open(tempdir.name + '/configs/' + device['hostname'] + '.cfg', 'w') as f:
                cfg=libreapi.i_get_oxidized_config(device['hostname'])
                if type(cfg) == str and cfg != "node not found":
                    f.write(cfg)
                    print(device['sysName'])

#Download configs from Oxid into Temp directory compatible with Batfish
tempdir=tempfile.TemporaryDirectory()
os.mkdir(tempdir.name + "/configs")
download_config(tempdir,'ios')
download_config(tempdir,'iosxe')
download_config(tempdir,'iosxr')
download_config(tempdir,'nxos','aci')

#Upload configs from Temp directory to Batfish
bf = Session(host="localhost")
bf.set_network("Auto-Import")
bf.init_snapshot(tempdir.name, name="Full", overwrite=True)

#Test Q/A to Batfish
#answer=bf.q.nodeProperties().answer() 
#answer_df = answer.frame()
#answer_df.to_csv('output.csv')
