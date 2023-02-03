#This script clears Dependency Map of all Device dependencies.

from Libs.LibreNMSAPIClient import LibreNMSAPIClient
libreapi=LibreNMSAPIClient()
print("Starting to Clear Dependencies")
for device in libreapi.list_devices():
    libreapi.i_delete_parents_from_host(device['device_id'])
    print("Dependency cleared for " +device['sysName'])

print("Done to Clearing Dependencies")
