#This script builds a Dependency Map in Libre first using FDB, then trying ARP, then trying xDP. 


from Libs.LibreNMSAPIClient import LibreNMSAPIClient
import sys
libreapi =  LibreNMSAPIClient()
device_dep_map={}



def update_Dependency(device,parents,device_dep_map):
    print("Parent found for " + device['sysName'] + "- " +str(parents))
    device_dep_map[str(device['device_id'])]=parents
    libreapi.i_delete_parents_from_host(device['device_id']) #Clear existing parent
    libreapi.i_add_parents_to_host({'parent_ids':",".join(parents)},device['device_id']) #Set new parents

def remove_loops(parents, device, device_dep_map):
    output=[]
    for parent in parents:
        if parent not in device_dep_map or (parent in device_dep_map and str(device['device_id']) not in device_dep_map[parent]) :
            output.append(parent)
        else:
            print("Loop prevented between " + str(device['device_id']) + " and " + parent)
    return output

def Try_xDP(device,device_dep_map): #Try looking up dependency by xDP Neighbor of polling port (longshot from my experience)
    polling_port_id = 0
    for address in libreapi.i_get_device_ip_addresses(device['device_id']): #Find port_id Libre is polling against
        if('ipv4_address' in address):
            if(device['hostname'] == address['ipv4_address'] or device['ip'] == address['ipv4_address']):
                polling_port_id = address['port_id']
                break
    if(polling_port_id != 0): # Check if Polling port was found
        parents=[]
        for link in libreapi.i_get_links(device['device_id']): #Find xDP neighbors of polling port
            if(link['local_port_id'] == polling_port_id and str(link['remote_device_id']) not in parents and link['remote_device_id'] != 0):
                 parents.append(str(link['remote_device_id']))
        parents=remove_loops(parents,device,device_dep_map) #Remove Dependency Loops
        if len(parents) == 1: 
            print("xDP to the rescue! for " + device['sysName'] + " - " + str(parents))
            update_Dependency(device,parents,device_dep_map)
            return True
    return False

def Try_FDB(Arp_entry,FDB,FDB_count_map,mac_count=1):
    parents=[]
    for entry in FDB: #Try FDB - Look up source port of Mac Address (Devices with ports where only this Mac is being learned.)
        if entry['mac_address'] == Arp_entry[0]['mac_address']:
            PID=str(entry['port_id'])
            if FDB_count_map[PID]['count']<= mac_count and str(FDB_count_map[PID]['device_id']) not in parents and FDB_count_map[PID]['device_id'] != device['device_id'] :
                parents.append(str(FDB_count_map[PID]['device_id']))
    return parents
original_stdout = sys.stdout
print("Starting!")
with open('Dependency_Generator.txt', 'w') as f:
    sys.stdout = f 

    #Define Stat counters
    fail_counter=0
    success_counter=0
    arp_notfound=0
    
    print("Downloading FDB")
    FDB=libreapi.oi_list_fdb()
    print("Downloading Device List")
    Devices=libreapi.list_devices()
    if len(FDB) == 0 :
        print("Downloading Full FDB Failed. Trying to get it by Device.")
        for device in Devices:
            FDB = FDB + libreapi.get_device_fdb(device['device_id'])
    print("Generating FDB Port-to-MAC entry count map")
    FDB_count_map={}
    for entry in FDB:
        counter_id=str(entry['port_id'])
        if counter_id in FDB_count_map:
                FDB_count_map[counter_id]['count']=FDB_count_map[counter_id]['count'] + 1
        else:
                FDB_count_map[counter_id]={'device_id':entry['device_id'],'count':1}
    print("Generating Dependency map for devices")
    for device in Devices:
        Arp_entry=libreapi.list_arp(device['hostname'] if device['ip'] == "" else device['ip'])
        if len(Arp_entry) > 0:
            parents=Try_FDB(Arp_entry,FDB,FDB_count_map,1)#Try FDB - allowing 1 MAC on the source port
            parents=remove_loops(parents,device,device_dep_map) #Remove Dependency Loops
            
            if(len(parents) == 0 or len(parents) > 2): #Try ARP - if too many or too few parents are found in FDB. (Devices where they're learning the MAC address.)
                parents=[]
                for arp_ent in Arp_entry:
                    port_info=libreapi.get_port_info(arp_ent['port_id'])[0]
                    port_did=str(port_info['device_id'])
                    if port_info['device_id'] != device['device_id'] and 'Mgmt' not in port_info['ifName'] and port_did not in parents:
                        parents.append(port_did)
                parents=remove_loops(parents,device,device_dep_map) #Remove Dependency Loops
                
                if(len(parents) == 0 or len(parents) > 2): #Try FDB again - this time allowing 2 MACs on the source port (Some devices have 2 MACs)
                    parents=Try_FDB(Arp_entry,FDB,FDB_count_map,2)
                    parents=remove_loops(parents,device,device_dep_map) #Remove Dependency Loops
                
            if len(parents) == 1 or len(parents) == 2: #Update found parents in Libre
                update_Dependency(device,parents,device_dep_map)
                success_counter=success_counter+1
            elif not Try_xDP(device,device_dep_map):
                print("Couldn't find parent for " + device['sysName'])
                fail_counter=fail_counter+1
        elif not Try_xDP(device,device_dep_map):
            print("ARP Not found for " + device['sysName'])
            arp_notfound=arp_notfound + 1
    print("Done!")
    print("Success: " + str(success_counter))
    print("Failed: " + str(fail_counter))
    print("Missing ARPs: " + str(arp_notfound))
    sys.stdout = original_stdout
    print("Done!")
