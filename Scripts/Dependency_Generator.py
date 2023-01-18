#This script builds a Dependency Map in Libre


from Libs.LibreNMSAPIClient import LibreNMSAPIClient #https://github.com/electrocret/LibreNMSAPIClient
import sys

class Dependency_Map:

    def child_count(self):
        children_count={}
        for did,parent_obj in self.Device_Dependency_Map.items():
            for parent in parent_obj.Parents:
                children_count[parent]=1 if parent not in children_count else children_count[parent] + 1
        return children_count
    
    def remove_loops(self):
        print("Searching for Dependency Loops")
        children_count=self.child_count()
        for child,parent_obj in self.Device_Dependency_Map.items():
            grandparents=parent_obj.grandparents(0)
            if child in grandparents: #High level check for loop
                for grandparent in grandparents:
                    if(grandparent in self.Device_Dependency_Map and child in self.Device_Dependency_Map[grandparent].Parents): #Find Loop source
                        print("Loop found between " + child + " and " + grandparent + " (" + str(children_count[child]) + ">" + str(children_count[grandparent]) + ")")
                        self.loops_prevented=self.loops_prevented + 1
                        if child != grandparent and children_count[child] > children_count[grandparent] or grandparent in parent_obj.Parents: #Determine who's the parent based on child count, then remove child.
                            self.Device_Dependency_Map[grandparent].Parents.remove(child)
                        else:
                            parent_obj.Parents.remove(grandparent)
        print("Finished searching for Dependency Loops")

    def try_ARP(self,exclude_monitoring_ports=True,max_allowed_parents=2,overwrite=False):
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
                    if port_info['device_id'] != device['device_id']  and port_did not in parents:
                        parents.append(port_did)
            self.build_dependency(Device,parents,"ARP",max_allowed_parents,overwrite)
        print("Finished building Dependency Map based on ARP")

    def try_xDP(self,max_allowed_parents=1,overwrite=False):
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

    def gen_dependency(self,Device,overwrite=False):
        return overwrite or str(Device['device_id']) not in self.Device_Dependency_Map or ( str(Device['device_id']) in self.Device_Dependency_Map and len(self.Device_Dependency_Map[str(Device['device_id'])].Parents) == 0)
    def build_dependency(self, Device, parents, Source,max_allowed_parents,overwrite=False):
        if len(parents) <= max_allowed_parents and len(parents) != 0 and self.gen_dependency(Device,overwrite) :
            print(Parent_Obj(self,Device,parents,Source))
    
    def stats_dependent_source(self,dsource):
        count=0
        for did,parent_obj in self.Device_Dependency_Map.items():
            if parent_obj.Source == dsource:
                count=count + 1
        return count
    
    def stats_dependents(self):
        return len(self.Device_Dependency_Map)
    
    def stats_independents(self):
        return len(self.libreapi.list_devices()) - len(self.Device_Dependency_Map)
    
    def stats_loops_prevented(self):
        return self.loops_prevented
    
    def update_libre(self,force=False):
        print("Updating Libre Dependency Map")
        for did,parent_obj in self.Device_Dependency_Map.items():
            parent_obj.update_libre(force)
        print("Finished updating Libre Dependency Map")

    def __init__(self,libreapi):
        self.Device_Dependency_Map={} # {<did>:Parent_Obj}}
        self.libreapi=libreapi
        self.loops_prevented=0


class Parent_Obj:
    def grandparents(self,depth=0):
        grandparents=[]
        for parent in self.Parents:
            if parent in self.DMap.Device_Dependency_Map:
                grandparents = grandparents + self.DMap.Device_Dependency_Map[parent].Parents
                if depth > 0:
                   grandparents = grandparents + self.DMap.Device_Dependency_Map[parent].grandparents(depth - 1)
        return list(dict.fromkeys(grandparents))
    
    def update_libre(self,force=False):
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



original_stdout = sys.stdout
print("Starting!")
with open('Dependency_Generator.txt', 'w') as f:
    sys.stdout = f 
    dep_map=Dependency_Map(LibreNMSAPIClient())
    dep_map.try_FDB()
    dep_map.remove_loops()
    dep_map.try_ARP()
    dep_map.remove_loops()
    dep_map.try_FDB(2)
    dep_map.remove_loops()
    dep_map.try_xDP()
    dep_map.remove_loops()
    print("Dependent Devices:" + str(dep_map.stats_dependents()))
    print("Independent Devices:" + str(dep_map.stats_independents()))
    print("FDB Dependents:" + str(dep_map.stats_dependent_source('FDB')))
    print("ARP Dependents:" + str(dep_map.stats_dependent_source('ARP')))
    print("xDP Dependents:" + str(dep_map.stats_dependent_source('xDP')))
    print("Loops prevented:" + str(dep_map.stats_loops_prevented()))
    dep_map.update_libre()
    sys.stdout = original_stdout
    print("Done!")
