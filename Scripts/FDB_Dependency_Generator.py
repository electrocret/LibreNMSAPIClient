#This Script builds Libre's dependency map based on the FDB.

from Libs.LibreNMSAPIClient import LibreNMSAPIClient
import sys
libreapi =  LibreNMSAPIClient()

original_stdout = sys.stdout
print("Starting!")
with open('FDB_Dependency_Generator.txt', 'w') as f:
    sys.stdout = f # Change the standard output to the file we created.
    fail_counter=0
    success_counter=0
    arp_rescue_counter=0
    print("Downloading FDB")
    FDB=libreapi.o_list_fdb()
    print("Generating FDB_count_map")
    FDB_count_map={}
    for entry in FDB:
        counter_id="pid" + str(entry['port_id'])
        if counter_id in FDB_count_map:
                FDB_count_map[counter_id]['count']=FDB_count_map[counter_id]['count'] + 1
        else:
                FDB_count_map[counter_id]={'device_id':entry['device_id'],'count':1}
    print("Generating Dependency map for devices")
    for device in libreapi.list_devices():
        Arp_entry=libreapi.list_arp(device['hostname'] if device['ip'] == "" else device['ip'])
        if len(Arp_entry) > 0:
            parents=[]
            for entry in FDB:
                if entry['mac_address'] == Arp_entry[0]['mac_address']:
                    counter_id="pid" + str(entry['port_id'])
                    if FDB_count_map[counter_id]['count']== 1 :
                        parents.append(str(FDB_count_map[counter_id]['device_id']))
            if((len(parents) == 0 or len(parents) > 2) and len(Arp_entry) == 1):
              print("ARP to the rescue! for " + device['sysName'] + "- " + str(parents))
              parents=[str(libreapi.get_port_info(Arp_entry[0]['port_id'])[0]['device_id'])]
              arp_rescue_counter=arp_rescue_counter + 1
            if len(parents) == 1 or len(parents) == 2: #If only 1 or 2 parents were found.
                print("Parent found for " + device['sysName'] + "- " +str(parents))
                libreapi.i_delete_parents_from_host(device['device_id']) #Clear existing parent
                libreapi.i_add_parents_to_host({'parent_ids':",".join(parents)},device['device_id']) #Set new parents
                success_counter=success_counter+1
            else:
                print("Couldn't find parent for " + device['sysName'])
                fail_counter=fail_counter+1
    print("Done!")
    print("Success: " + str(success_counter))
    print("Failed: " + str(fail_counter))
    print("ARP Rescues: " + str(arp_rescue_counter))
    sys.stdout = original_stdout
    print("Done!")
