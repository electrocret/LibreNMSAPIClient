#This script goes through all devices in the default poller group, and regroups them based on their dependency map parent.

from Libs.LibreNMSAPIClient import LibreNMSAPIClient
libreapi=LibreNMSAPIClient()

devices=libreapi.list_devices()
devices_byid={}
for device in devices:
    devices_byid[str(device['device_id'])]=device


def find_pollergroup(device): #Finds poller group based on parent
    if device['poller_group'] != 0:
        return device['poller_group']
    if device['dependency_parent_id']:
        for parent_id in device['dependency_parent_id'].split(","):
            parent_pollergroup=find_pollergroup(devices_byid[parent_id])
            if parent_pollergroup != 0:
                return parent_pollergroup
    return 0


def update_pollergroup(device):
    new_pollergroup=find_pollergroup(device)
    if new_pollergroup != 0:
        libreapi.update_device_field({'field':'poller_group','data':new_pollergroup},device['device_id'])
        print("Group Updated!")
        return True
    return False

  
for device in devices:
    if device['poller_group'] == 0:
        print(device['sysName'])
        update_pollergroup(device)
print("DONE!")
