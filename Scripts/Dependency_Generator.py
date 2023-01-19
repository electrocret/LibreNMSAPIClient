#This script builds a Dependency Map in Libre

from Libs.LibreNMSAPIClient import LibreNMSAPIClient #https://github.com/electrocret/LibreNMSAPIClient
import sys
from datetime import date

class Dependency_Map:
    """ Dependency_Map Class creates an object for building Libre Dependency Maps"""
    def child_count(self):
        """returns dict of Counts of the direct children of each device. {'device_id':count} """
        children_count={}
        for did,Dependency_Obj in self.Device_Dependency_Map.items():
            for parent in Dependency_Obj.Parents:
                children_count[parent]=1 if parent not in children_count else children_count[parent] + 1
        return children_count
    
    def remove_loops(self):
        """Searches through Dependency Map looking for loops. Currently only looks at direct parent/child relationships and doesn't look at grandchildren"""
        print("Searching for Dependency Loops")
        children_count=self.child_count()
        for child,Dependency_Obj in self.Device_Dependency_Map.items():
            grandparents=Dependency_Obj.grandparents(0)
            if child in grandparents: #High level check for loop
                for grandparent in grandparents:
                    if(grandparent in self.Device_Dependency_Map and child in self.Device_Dependency_Map[grandparent].Parents): #Find Loop source
                        print("Loop found between " + child + " and " + grandparent + " (Child Tiebreaker:" + str(children_count[child]) + ">" + str(children_count[grandparent]) + ")")
                        self.loops_prevented=self.loops_prevented + 1
                        if child != grandparent and children_count[child] > children_count[grandparent] or grandparent in Dependency_Obj.Parents: #Determine who's the parent based on child count, then remove child.
                            self.Device_Dependency_Map[grandparent].Parents.remove(child)
                        else:
                            Dependency_Obj.Parents.remove(grandparent)
        print("Finished searching for Dependency Loops")

    def try_ARP(self,exclude_monitoring_ports=True,max_allowed_parents=2,overwrite=False):
        """
            Finds Dependencies based on ARP.

            Parameters:
             exclude_monitoring_ports - Boolean - Whether to exclude ports that Libre is monitoring against for parental consideration.
             max_allowed_parents - int - Maximum number of parents allowed. If exceeded then no valid parent is considered found. (2 is generaly a good number. For HSRP/VRRP Gateways)
             overwrite - boolean - Whether to overwrite existing Dependency Map mappings that may have been found by previous functions.

        """
        Monitored_IPs=[]
        for device in self.libreapi.list_devices():
            Monitored_IPs.append(device['hostname'] if device['ip'] == "" else device['ip'])
        print("Building Dependency Map based on ARP")
        for Device in self.libreapi.list_devices():
            if not self.gen_dependency(Device,overwrite):
                continue
            parents=[]
            for arp_ent in self.libreapi.list_arp(Device['hostname'] if Device['ip'] == "" else Device['ip']):
                monitoring_port=False
                if exclude_monitoring_ports:
                    for port_ip in self.libreapi.i_get_port_ip_info(arp_ent['port_id']):
                        if 'ipv4_address' in port_ip and port_ip['ipv4_address'] in Monitored_IPs:
                            monitoring_port=True
                            break
                if not monitoring_port:
                    port_info=self.libreapi.get_port_info(arp_ent['port_id'])[0]
                    port_did=str(port_info['device_id'])
                    if port_info['device_id'] != Device['device_id'] and port_did not in parents:
                        parents.append(port_did)
            self.build_dependency(Device,parents,"ARP",max_allowed_parents,overwrite)
        print("Finished building Dependency Map based on ARP")
        
    def try_Network_Neighbors(self,max_allowed_parents=2,overwrite=False):
        """
            Makes educated guess as to what the parent of a device is based on what's most common parent among other hosts in the network.
            
            Parameters:
             max_allowed_parents - int - Maximum number of parents function will set
             overwrite - boolean - Whether to overwrite existing Dependency Map mappings that may have been found by previous functions.
        """
        print("Building Dependency Map based on Network Neighbors")
        for Device in self.libreapi.list_devices():
            if not self.gen_dependency(Device,overwrite):
                continue
            polling_network_id = 0
            for address in self.libreapi.i_get_device_ip_addresses(Device['device_id']):
                if('ipv4_address' in address):
                    if(Device['hostname'] == address['ipv4_address'] or Device['ip'] == address['ipv4_address']):
                        polling_network_id = address['ipv4_network_id']
                        break
            if(polling_network_id != 0): # Check if Polling network was found
                parents=[]
                for address in self.libreapi.get_network_ip_addresses(polling_network_id):
                    did=str(self.libreapi.get_port_info(address['port_id'])[0]['device_id'])
                    if did in self.Device_Dependency_Map and self.Device_Dependency_Map[did].Source != "Network_Neighbors":
                        parents=parents + self.Device_Dependency_Map[did].Parents
                if len(parents) > 0:
                    if str(Device['device_id']) in parents:
                        while str(Device['device_id']) in parents:
                            parents.remove(str(Device['device_id']))
                    dedup_parents=list(dict.fromkeys(parents))
                    while len(parents) > max_allowed_parents:
                        for parent in dedup_parents:
                            if parent in parents and len(parents) > max_allowed_parents:
                                parents.remove(parent)
                    self.build_dependency(Device,parents,"Network_Neighbors",max_allowed_parents,overwrite)
        print("Finished building Dependency Map based on Network Neighbors")
        
    def try_xDP(self,max_allowed_parents=1,overwrite=False):
        """
            Finds Dependencies based on xDP (CDP/LLDP).

            Parameters:
             max_allowed_parents - int - Maximum number of parents allowed. If exceeded then no valid parent is considered found.
             overwrite - boolean - Whether to overwrite existing Dependency Map mappings that may have been found by previous functions.

             Note: From my experience, this method isn't very reliable since the Libre's Discovery module needs some TLC.

        """
        print("Building Dependency Map based on xDP")
        for Device in self.libreapi.list_devices():
            if not self.gen_dependency(Device,overwrite):
                continue
            polling_port_id = 0
            for address in self.libreapi.i_get_device_ip_addresses(Device['device_id']):
                if('ipv4_address' in address):
                    if(Device['hostname'] == address['ipv4_address'] or Device['ip'] == address['ipv4_address']):
                        polling_port_id = address['port_id']
                        break
            if(polling_port_id != 0): # Check if Polling port was found
                parents=[]
                for link in self.libreapi.i_get_links(Device['device_id']): #Find xDP neighbors of polling port
                    if(link['local_port_id'] == polling_port_id and link['remote_device_id'] not in parents and link['remote_device_id'] != 0):
                         parents.append(link['remote_device_id'])
                self.build_dependency(Device,parents,"xDP",max_allowed_parents,overwrite)
        print("Finished building Dependency Map based on xDP")
        
    def try_FDB(self,allowed_mac_count=1,max_allowed_parents=2,overwrite=False):
        """
            Finds Dependencies based on FDB.

            Parameters:
             allowed_mac_count - int - Number of MACs that can be discovered on a port for it to be considered a source port. (Libre's algorithm uses 1, however some devices have multiple MACs)
             max_allowed_parents - int - Maximum number of parents allowed. If exceeded then no valid parent is considered found.
             overwrite - boolean - Whether to overwrite existing Dependency Map mappings that may have been found by previous functions.

        """
        print("Downloading FDB")
        FDB=self.libreapi.oi_list_fdb()
        if len(FDB) == 0 :
            print("Downloading Full FDB Failed. Trying to get it by Device.")
            for device in self.libreapi.list_devices():
                FDB = FDB + self.libreapi.get_device_fdb(device['device_id'])
        FDB_count_map={}
        for entry in FDB:
            counter_id=str(entry['port_id'])
            if counter_id in FDB_count_map:
                FDB_count_map[counter_id]['count']=FDB_count_map[counter_id]['count'] + 1
            else:
                FDB_count_map[counter_id]={'device_id':entry['device_id'],'count':1}
        print("Building Dependency Map based on FDB")
        for Device in self.libreapi.list_devices():
            if not self.gen_dependency(Device,overwrite):
                continue
            Arp_Entries=self.libreapi.i_list_arp(Device['hostname'] if Device['ip'] == "" else Device['ip'])
            if len(Arp_Entries) > 0:
                parents=[]
                for entry in FDB: #Try FDB - Look up source port of Mac Address (Devices with ports where only this Mac is being learned.)
                    if entry['mac_address'] == Arp_Entries[0]['mac_address']:
                        PID=str(entry['port_id'])
                        if FDB_count_map[PID]['count']<= allowed_mac_count and str(FDB_count_map[PID]['device_id']) not in parents and FDB_count_map[PID]['device_id'] != Device['device_id'] :
                            parents.append(str(FDB_count_map[PID]['device_id']))
                self.build_dependency(Device,parents,"FDB",max_allowed_parents,overwrite)
        print("Finished building Dependency Map based on FDB")

    def set_dependency(self,Children,parents,overwrite=False):
        """
            Staticly sets dependency

            Parameters:
             Children - List - List of Device IDs to set Parent for
             Parents - List - List of Parent Device IDs
             overwrite - boolean - Whether to overwrite existing Dependency Map mappings that may have been found by previous functions.

        """
        for Device in self.libreapi.list_devices():
            if str(Device['device_id']) in Children:
                self.build_dependency(Device,parents,"static",len(parents),overwrite,len(parents))
        
    def gen_dependency(self,Device,overwrite=False):
        """
            Tells try functions whether they should try to generate a dependency.
            Based on whether a dependency already exists for the Device in the Device_Dependency_Map

            Parameters:
                Device - Dict - Device Dictionary from Libre
                overwrite - boolean - Overwrite variable given to "try_" functions
        """
        return overwrite or str(Device['device_id']) not in self.Device_Dependency_Map or ( str(Device['device_id']) in self.Device_Dependency_Map and len(self.Device_Dependency_Map[str(Device['device_id'])].Parents) == 0)


    def build_dependency(self, Device, parents, Source,max_allowed_parents,overwrite=False,min_parents=1):
        """
            Builds dependency Dependency_Obj.

            Parameters:
                Device - Dict - Device Dictionary from Libre
                Source - Str - Name for source function. (used internally for stats & diagnostics)
                max_allowed_parents - int - Maximum number of parents allowed. If exceeded then no valid parent is considered found.
                overwrite - boolean - Whether to overwrite existing Dependency Map mappings that may have been found by previous functions.
                min_parents - int - Minimum number of parents allowed.
        """
        if len(parents) <= max_allowed_parents and len(parents) >= min_parents and self.gen_dependency(Device,overwrite) :
            print(Dependency_Obj(self,Device,parents,Source))
    
    def stats_dependent_source(self,dSource):
        """
            Returns an int count of how many dependencies were found from this source.
            Parameters:
                dSource - Str - String each source identifies by ie. ARP,FDB,xDP
        """
        count=0
        for did,Dependency_Obj in self.Device_Dependency_Map.items():
            if Dependency_Obj.Source == dSource:
                count=count + 1
        return count
    
    def stats_dependents(self):
        """
            Returns an int count of how many dependencies are in the map.
        """
        return len(self.Device_Dependency_Map)
    
    def stats_independents(self):
        """
            Returns an int count of how many dependencies aren't in the map.
        """
        return len(self.libreapi.list_devices()) - len(self.Device_Dependency_Map)
    
    def stats_loops_prevented(self):
        """
            Returns an int count of how many loops were found & prevented using the remove_loops function.
        """
        return self.loops_prevented
    
    def update_libre(self,force=False):
        """
            Updates Libre's dependency map with Dependency_Map Object's Map.
            Parameters:
                force - boolean - Forces update to Libre even if the Dependency_Obj has no parents. (When false - if Dependency_Obj has no Parent in it then it will be skipped)
        """
        print("Updating Libre Dependency Map")
        for did,Dependency_Obj in self.Device_Dependency_Map.items():
            Dependency_Obj.update_libre(force)
        print("Finished updating Libre Dependency Map")

    def __init__(self,libreapi):
        self.Device_Dependency_Map={} # {<did>:Dependency_Obj}}
        self.libreapi=libreapi
        self.loops_prevented=0


class Dependency_Obj:
    def grandparents(self,depth=0):
        """
            Returns a list of this Dependency_Obj's Parent device IDs
            Parameters:
                depth - int - How many generations to go back
        """
        grandparents=[]
        for parent in self.Parents:
            if parent in self.DMap.Device_Dependency_Map:
                grandparents = grandparents + self.DMap.Device_Dependency_Map[parent].Parents
                if depth > 0:
                   grandparents = grandparents + self.DMap.Device_Dependency_Map[parent].grandparents(depth - 1)
        return list(dict.fromkeys(grandparents))

    def update_libre(self,force=False):
        """
            Updates Libre's dependency map with this Dependency_Obj.
            Parameters:
                force - boolean - Forces update to Libre even if the Dependency_Obj has no parents. (When false - if Dependency_Obj has no Parent in it then it will be skipped)
        """
        if len(self.Parents) > 0 or force:
            self.DMap.libreapi.i_delete_parents_from_host(self.Device_ID) #Clear existing parent
            if len(self.Parents) > 0:
                self.DMap.libreapi.i_add_parents_to_host({'parent_ids':",".join(self.Parents)},self.Device_ID) #Set new parents
            
    def __init__(self,DMap,Device,Parent_List,Source=""):
        self.Device_ID=str(Device['device_id'])
        DMap.Device_Dependency_Map[self.Device_ID]=self
        self.DMap=DMap
        self.Source=Source
        self.Parents=[]
        for Parent in Parent_List:
            self.Parents.append(str(Parent))
    def __str__(self):
        return "Device:" + self.Device_ID + " Parents:" + str(self.Parents) + " Source:" +self.Source




### Script Start ###
    
original_stdout = sys.stdout
print("Starting!")
with open('Dependency_Generator.txt', 'w') as f:
    sys.stdout = f
    print("Executed: " + str(date.today()))
    dep_map=Dependency_Map(LibreNMSAPIClient())
    dep_map.try_FDB() #Try to find endpoint switchport of Device. (Uses similar algorithm to Libre's FDB)
    dep_map.try_FDB(2) #Try to find endpoint switchport of Device. (Uses similar algorithm to Libre's FDB except with the allowance of 2 MAC's sourced from port. For compatibility with some devices.)
    dep_map.remove_loops()
    dep_map.try_xDP() #Try to find endpoint switchport using xDP.
    dep_map.remove_loops()
    dep_map.try_ARP() #Try to find Device's GW using ARP.
    dep_map.remove_loops()
    dep_map.try_Network_Neighbors() #Make Educated guess based on peers in Device's network.
    dep_map.remove_loops()
    print("##Dependency Generator Stats##")
    print("Dependent Devices:" + str(dep_map.stats_dependents()))
    print("Independent Devices:" + str(dep_map.stats_independents()))
    print("FDB Dependents:" + str(dep_map.stats_dependent_source('FDB')))
    print("ARP Dependents:" + str(dep_map.stats_dependent_source('ARP')))
    print("xDP Dependents:" + str(dep_map.stats_dependent_source('xDP')))
    print("Network Neightbor Dependents:" + str(dep_map.stats_dependent_source('Network_Neighbors')))
    print("Loops prevented:" + str(dep_map.stats_loops_prevented()))
    dep_map.update_libre() #Update Dependency Map in Libre
    sys.stdout = original_stdout
    print("Done!")
