#!/bin/python
import requests
import json
import os
import re



##
##Function Flags:  
## i-ignore response error.
## l-return response in list even if there's only one response/request
## e-entire response. Returns entire JSON object response
## r-raw response object that was received from requests. Skips all JSON conversion and most validation.
## c-combines all of the API responses into a single list instead of a separate list for each response.
## o-optional - makes all parameters optional.
##

class LibreNMSAPIClientException(Exception):
        def __init__(self, message):
                super(LibreNMSAPIClientException, self).__init__(message)


class LibreNMSAPIClient:
    functions = {
#        'example_function' : {
#            'route': '/route/:to/function/:param',
#            'request_method': 'GET',
#            'response_key':'key', -specify's the response key API call returns otherwise gets 'message' value or 'status' value
#            'flags':'', -Any required function flags.
#        },
        'list_functions' : {
            'route': '/api/v0/',
            'request_method': 'GET',
            'flags': 'e'
        },
        'get_alert' : {
            'route': '/api/v0/alerts/:id',
            'request_method': 'GET',
            'response_key':'alerts',
        },
        'ack_alert' : {
            'route': '/api/v0/alerts/:id',
            'request_method': 'PUT',
        },
        'unmute_alert' : {
            'route': '/api/v0/alerts/unmute/:id',
            'request_method': 'PUT',
        },
        'list_alerts' : {
            'route': '/api/v0/alerts',
            'request_method': 'GET',
            'response_key':'alerts',
        },
        'get_alert_rule' : {
            'route': '/api/v0/rules/:id',
            'request_method': 'GET',
            'response_key':'rules',
        },
        'delete_rule' : {
            'route': '/api/v0/rules/:id',
            'request_method': 'DELETE',
        },
        'list_alert_rules' : {
            'route': '/api/v0/rules',
            'request_method': 'GET',
            'response_key':'rules',
        },
        'add_rule' : {
            'route': '/api/v0/rules',
            'request_method': 'POST',
            'response_key':'alerts',
        },
        'edit_rule' : {
            'route': '/api/v0/rules',
            'request_method': 'PUT',
        },
        'list_arp' : {  
            'route': '/api/v0/resources/ip/arp/:query',
            'request_method': 'GET',
            'response_key':'arp',
        },
        'list_bills' : {
            'route': '/api/v0/bills',
            'request_method': 'GET',
            'response_key':'bills',
        },
        'get_bill' : {
            'route': '/api/v0/bills/:id',
            'request_method': 'GET',
            'response_key':'bills',
        },
        'get_bill_graph' : {    #Need to look into compatibility. docs say response is graph image
            'route': '/api/v0/bills/:id/graphs/:graph_type',
            'request_method': 'GET',
        },
        'get_bill_graphdata' : { #Need to look into compatibility. docs don't show graph_data as a list which isn't normal.
            'route': '/api/v0/bills/:id/graphdata/:graph_type',
            'request_method': 'GET',
            'response_key':'graph_data',
        },
        'get_bill_history' : {
            'route': '/api/v0/bills/:id/history',
            'request_method': 'GET',
            'response_key':'bill_history',
        },
        'get_bill_history_graph' : {    #Need to look into compatibility. docs say response is graph image
            'route': '/api/v0/bills/:id/history/:bill_hist_id/graphs/:graph_type',
            'request_method': 'GET',
        },
        'get_bill_history_graphdata' : { #Need to check compatibility. docs don't specify response. (Guessed based off of get_bill_graphdata)
            'route': '/api/v0/bills/:id/history/:bill_hist_id/graphdata/:graph_type',
            'request_method': 'GET',
            'response_key':'graph_data',
        },
        'delete_bill' : {
            'route': '/api/v0/bills/:id',
            'request_method': 'DELETE',
        },
        'create_edit_bill' : {
            'route': '/api/v0/bills',
            'request_method': 'POST',
            'response_key':'bill_id',
        },
        'get_devicegroups' : {
            'route': '/api/v0/devicegroups',
            'request_method': 'GET',
            'response_key':'groups',
        },
        'add_devicegroup' : {
            'route': '/api/v0/devicegroups',
            'request_method': 'POST',
            'response_key':'id', 
        },
        'get_devices_by_group' : {
            'route': '/api/v0/devicegroups/:name',
            'request_method': 'GET',
            'response_key':'devices'
        },
        'maintenance_devicegroup' : {
            'route': '/api/v0/devicesgroups/:name/maintenance',
            'request_method': 'POST',
        },
        'del_device' : {
            'route': '/api/v0/devices/:hostname',
            'request_method': 'DELETE',
            'response_key':'devices',
        },
        'get_device' : {
            'route': '/api/v0/devices/:hostname',
            'request_method': 'GET',
            'response_key':'devices',
        },
        'discover_device' : {
            'route': '/api/v0/devices/:hostname/discover',
            'request_method': 'GET',
        },
        'availability' : {
            'route': '/api/v0/devices/:hostname/availability',
            'request_method': 'GET',
            'response_key':'availability',
        },
        'outages' : {
            'route': '/api/v0/devices/:hostname/outages',
            'request_method': 'GET',
            'response_key':'outages',
        },
        'get_graphs' : {
            'route': '/api/v0/devices/:hostname/graphs',
            'request_method': 'GET',
            'response_key':'graphs',
        },
        'list_available_health_graphs' : {
            'route': '/api/v0/devices/:hostname/health/:type/:sensor_id',
            'request_method': 'GET',
            'response_key':'graphs',
            'flags':'o'
        },
        'list_available_wireless_graphs' : {
            'route': '/api/v0/devices/:hostname/wireless/:type/:sensor_id',
            'request_method': 'GET',
            'response_key':'graphs',
            'flags':'o'
        },
        'get_health_graph' : { #Doesn't support yet. output is graph image
            'route': '/api/v0/devices/:hostname/graphs/health/:type/:sensor_id',
            'request_method': 'GET',
            'flags':'o'
        },
        'get_wireless_graph' : { #Doesn't support yet. output is graph image
            'route': '/api/v0/devices/:hostname/graphs/wireless/:type/:sensor_id',
            'request_method': 'GET',
            'flags':'o'
        },
        'get_graph_generic_by_hostname' : { #Need to look into compatibility. docs say response is graph image
            'route': '/api/v0/devices/:hostname/:type',
            'request_method': 'GET',
        },
        'get_port_graphs' : {
            'route': '/api/v0/devices/:hostname/ports',
            'request_method': 'GET',
            'response_key':'ports',
        },
        'get_device_fdb' : {
            'route': '/api/v0/devices/:hostname/fdb',
            'request_method': 'GET',
            'response_key':'ports_fdb', 
        },
        'get_device_ip_addresses' : {
            'route': '/api/v0/devices/:hostname/ip',
            'request_method': 'GET',
            'response_key':'addresses',
        },
        'get_port_stack' : {
            'route': '/api/v0/devices/:hostname/port_stack',
            'request_method': 'GET',
            'response_key':'mappings',
        },
        'get_components' : {
            'route': '/api/v0/devices/:hostname/components',
            'request_method': 'GET',
            'response_key':'components',
        },
        'add_components' : {
            'route': '/api/v0/devices/:hostname/components/:type',
            'request_method': 'POST',
            'response_key':'components',
        },
        'edit_components' : {
            'route': '/api/v0/devices/:hostname/components',
            'request_method': 'PUT',
        },
        'delete_components' : {
            'route': '/api/v0/devices/:hostname/components/:component',
            'request_method': 'DELETE',
        },
        'get_port_stats_by_port_hostname' : {
            'route': '/api/v0/devices/:hostname/ports/:ifname',
            'request_method': 'GET',
            'response_key':'port', 
        },
        'get_graph_by_port_hostname' : {  #Need to look into compatibility. docs say response is graph image
            'route': '/api/v0/devices/:hostname/ports/:ifname/:type',
            'request_method': 'GET',
        },
        'list_locations' : {
            'route': '/api/v0/resources/locations',
            'request_method': 'GET',
            'response_key':'locations', 
        },
        'list_sensors' : {
            'route': '/api/v0/resources/sensors',
            'request_method': 'GET',
            'response_key':'sensors', 
        },
        'list_devices' : {
            'route': '/api/v0/devices',
            'request_method': 'GET',
            'response_key':'devices', 
        },
        'maintenance_device' : {
            'route': '/api/v0/devices/:hostname/maintenance',
            'request_method': 'POST',
        },
        'add_device' : {
            'route': '/api/v0/devices',
            'request_method': 'POST',
            'response_key':'devices', 
        },
        'list_oxidized' : {  #Doesn't support per docs. JSON output isn't in a dictionary per docs. Workaround: json.loads(libreapi.r_list_oxidized().text)
            'route': '/api/v0/oxidized/:hostname',
            'request_method': 'GET',
            'flags':'o'
        },
        'update_device_field' : {
            'route': '/api/v0/devices/:hostname',
            'request_method': 'PATCH',
        },
        'update_device_port_notes' : {
            'route': '/api/v0/devices/:hostname/port/:portid',
            'request_method': 'PATCH',
        },
        'rename_device' : {
            'route': '/api/v0/devices/:hostname/rename/:new_hostname',
            'request_method': 'PATCH',
        },
        'get_device_groups' : {
            'route': '/api/v0/devices/:hostname/groups',
            'request_method': 'GET',
            'response_key':'groups', 
        },
        'search_oxidized' : {
            'route': 'api/v0/oxidized/config/search/:searchstring',
            'request_method': 'GET',
            'response_key':'nodes', 
        },
        'get_oxidized_config' : { #Doesn't support per docs. JSON output isn't in a dictionary per docs. Workaround: json.loads(libreapi.ri_get_oxidized_config(device['hostname']).text)
            'route': '/api/v0/oxidized/config/:device_name',
            'request_method': 'GET',
            'response_key':'config', 
        },
        'add_parents_to_host' : {
            'route': '/api/v0/devices/:device/parents',
            'request_method': 'POST',
        },
        'delete_parents_from_host' : {
            'route': '/api/v0/devices/:device/parents',
            'request_method': 'DELETE',
        },
        'get_inventory' : {
            'route': '/api/v0/inventory/:hostname',
            'request_method': 'GET',
            'response_key':'inventory', 
        },
        'get_inventory_for_device' : {
            'route': '/api/v0/inventory/:hostname/all',
            'request_method': 'GET',
            'response_key':'inventory', 
        },
        'add_location' : {
            'route': '/api/v0/locations/',
            'request_method': 'POST',
        },
        'edit_location' : {
            'route': '/api/v0/locations/location',
            'request_method': 'PATCH',
        },
        'list_eventlog' : {
            'route': '/api/v0/logs/eventlog/:hostname',
            'request_method': 'GET',
            'response_key':'logs', 
        },
        'list_syslog' : {
            'route': '/api/v0/logs/syslog/:hostname',
            'request_method': 'GET',
            'response_key':'logs', 
        },
        'list_alertlog' : {
            'route': '/api/v0/logs/alertlog/:hostname',
            'request_method': 'GET',
            'response_key':'logs', 
        },
        'list_authlog' : {
            'route': '/api/v0/logs/authlog/:hostname',
            'request_method': 'GET',
            'response_key':'logs', 
        },
        'get_port_groups' : {
            'route': '/api/v0/port_groups',
            'request_method': 'GET',
            'response_key':'groups', 
        },
        'get_ports_by_group' : {
            'route': '/api/v0/port_groups/:name',
            'request_method': 'GET',
            'response_key':'ports', 
        },
        'add_port_group' : {
            'route': '/api/v0/port_groups',
            'request_method': 'POST',
            'response_key':'id', 
        },
        'assign_port_group' : {
            'route': '/api/v0/port_groups/:port_group_id/assign',
            'request_method': 'POST',
        },
        'remove_port_group' : {
            'route': '/api/v0/port_groups/:port_group_id/remove',
            'request_method': 'POST',
        },
        'get_graph_by_portgroup' : { #Need to look into compatibility. docs say response is graph image
            'route': '/api/v0/portgroups/:group',
            'request_method': 'GET',
        },
        'get_graph_by_portgroup_multiport_bits' : { #Need to look into compatibility. docs say response is graph image
            'route': '/api/v0/portgroups/multiport/bits/:id',
            'request_method': 'GET',
        },
        'get_all_ports' : {
            'route': '/api/v0/ports',
            'request_method': 'GET',
            'response_key':'ports', 
        },
        'search_ports' : {
            'route': '/api/v0/ports/search/:field/:search',
            'request_method': 'GET',
            'response_key':'ports',
            'flags':'o'
        },
        'ports_with_associated_mac' : {
            'route': '/api/v0/ports/mac/:search',
            'request_method': 'GET',
            'response_key':'port', 
        },
        'get_port_info' : {
            'route': '/api/v0/ports/:portid',
            'request_method': 'GET',
            'response_key':'port', 
        },
        'get_port_ip_info' : {
            'route': '/api/v0/ports/:portid/ip',
            'request_method': 'GET',
            'response_key':'addresses', 
        },
        'list_bgp' : {
            'route': '/api/v0/bgp',
            'request_method': 'GET',
            'response_key':'bgp_sessions', 
        },
        'get_bgp' : {
            'route': '/api/v0/bgp/:id',
            'request_method': 'GET',
            'response_key':'bgp_session', 
        },
        'edit_bgp_descr' : {
            'route': '/api/v0/bgp/:id',
            'request_method': 'POST',
        },
        'list_cbgp' : {
            'route': '/api/v0/routing/bgp/cbgp',
            'request_method': 'GET',
            'response_key':'bgp_counters', 
        },
        'list_ip_addresses' : {
            'route': '/api/v0/resources/ip/addresses',
            'request_method': 'GET',
            'response_key':'ip_addresses', 
        },
        'get_network_ip_addresses' : {
            'route': '/api/v0/resources/ip/networks/:id/ip',
            'request_method': 'GET',
            'response_key':'addresses', 
        },
        'list_ip_networks' : {
            'route': '/api/v0/resources/ip/networks',
            'request_method': 'GET',
            'response_key':'ip_networks', 
        },
        'list_ipsec' : {
            'route': '/api/v0/routing/ipsec/data/:hostname',
            'request_method': 'GET',
            'response_key':'ipsec', 
        },
        'list_ospf' : {
            'route': '/api/v0/ospf',
            'request_method': 'GET',
            'response_key':'ospf_neighbours', 
        },
        'list_ospf_ports' : {
            'route': '/api/v0/ospf_ports',
            'request_method': 'GET',
            'response_key':'ospf_ports', 
        },
        'list_vrf' : {
            'route': '/api/v0/routing/vrf',
            'request_method': 'GET',
            'response_key':'vrfs', 
        },
        'get_vrf' : {
            'route': '/api/v0/routing/vrf/:id',
            'request_method': 'GET',
            'response_key':'vrf', 
        },
        'list_mpls_services' : {
            'route': '/api/v0/routing/mpls/services',
            'request_method': 'GET',
            'response_key':'mpls_services', 
        },
        'list_mpls_saps' : {
            'route': '/api/v0/routing/mpls/saps',
            'request_method': 'GET',
            'response_key':'saps', 
        },
        'list_services' : {
            'route': '/api/v0/services',
            'request_method': 'GET',
            'response_key':'services', 
        },
        'get_service_for_host' : {
            'route': '/api/v0/services/:hostname',
            'request_method': 'GET',
            'response_key':'services', 
        },
        'add_service_for_host' : {
            'route': '/api/v0/services/:hostname',
            'request_method': 'POST', 
        },
        'edit_service_from_host' : {
            'route': '/api/v0/services/:service_id',
            'request_method': 'PATCH',
        },
        'delete_service_from_host' : {
            'route': '/api/v0/services/:service_id',
            'request_method': 'DELETE',
        },
        'list_vlans' : {
            'route': '/api/v0/resources/vlans',
            'request_method': 'GET',
            'response_key':'vlans', 
        },
        'get_vlans' : {
            'route': '/api/v0/devices/:hostname/vlans',
            'request_method': 'GET',
            'response_key':'vlans', 
        },
        'list_links' : {
            'route': '/api/v0/resources/links',
            'request_method': 'GET',
            'response_key':'links', 
        },
        'get_links' : {
            'route': '/api/v0/devices/:hostname/links',
            'request_method': 'GET',
            'response_key':'links', 
        },
        'get_link' : {
            'route': '/api/v0/resources/links/:id',
            'request_method': 'GET',
            'response_key':'links', 
        },
        'list_fdb' : {
            'route': '/api/v0/resources/fdb/:mac',
            'request_method': 'GET',
            'response_key':'ports_fdb', 
        },
        'system' : {
            'route': '/api/v0/system',
            'request_method': 'GET',
            'response_key':'system', 
        },
    }
    #Generates Query Parameters
    def _gen_qparams(self,qparams,first_qparam=True,param_value=False):
        output=''
        for qparam in qparams:
                if type(qparam) == str:
                        if qparam == "":
                                continue
                        if param_value:
                              output = output + '=' + qparam
                              param_value=False
                        elif first_qparam is True:
                                output = output + '?' + qparam
                                first_qparam=False
                                param_value=True
                        else:
                                output = output + '&' + qparam
                                param_value=True
                elif type(qparam) == list:
                        nest_output,first_qparam=self._gen_qparams(qparam,first_qparam,param_value)
                        output= output + nest_output
                else:
                        raise LibreNMSAPIClientException("API received unsupported parameter value: %s " % param)
        return output,first_qparam       
    #Generates Route using parameters
    def _gen_route(self,route,params):
        if len(params) == 0:
                if re.findall('\/:.*',route):
                        route=re.sub('\/:.*',"",route,1)
                return [route]
        if re.findall('\/:',route) : #Checks if any params are in URL path ( /: ) ie required parameter.
               param=params.pop()
               if type(param) == list :
                        output = list()
                        for subparam in param:
                                subparams = params.copy()
                                subparams.append(subparam)
                                output = output + self._gen_route(route,subparams)
                        return output
               elif type(param) == int or str:
                        if param == "":
                                if 'o' in self._flags:
                                        if re.findall('/:.*?/',route) :
                                          return self._gen_route(re.sub('/:.*?/',"/",route, 1).rstrip("/"),params)
                                        return self._gen_route(re.sub('\/:.*',"/" ,route, 1).rstrip("/"),params)
                                raise LibreNMSAPIClientException("API received empty parameter for %s" % route)
                        if re.findall('/:.*?/',route) :
                          return self._gen_route(re.sub('/:.*?/',"/%s/" % param,route, 1),params)
                        return self._gen_route(re.sub('\/:.*',"/%s" % param,route, 1),params)
               raise LibreNMSAPIClientException("API received unsupported parameter value: %s " % param)
        if params:
                params.reverse()
                qparams,fp=self._gen_qparams(params)
                route = route + qparams
        return [route]

    #Performs API Call
    def _apicall(self, *t_params):
        params=list(t_params)
        params.reverse()
        if self.functions[self._function_name]['request_method'] in ['POST','PATCH']: #Retrieve request data for request_methods that need input data.
            if not params:
                raise LibreNMSAPIClientException("API '%s' function called without required request data." % self._function_name)
            request_data = params.pop()

        if len(re.findall('\/:',self.functions[self._function_name]['route'])) > len(params) and 'o' not in self._flags: #Ensures the needed number of Route parameters are provided
            raise LibreNMSAPIClientException("API '%s' function called without required parameters." % self._function_name)
        routes=self._gen_route(self.functions[self._function_name]['route'],params) #Generate Function Route/s with parameters
        responses=[]
        if(self.functions[self._function_name]['request_method'] == 'DELETE'):
                        for route in routes:
                                responses.append(requests.delete( self._libre_url + route, headers=self._header, verify = False))
        elif(self.functions[self._function_name]['request_method'] == 'GET'):
                        for route in routes:
                                responses.append(requests.get( self._libre_url + route, headers=self._header, verify = False))
        elif(self.functions[self._function_name]['request_method'] == 'PATCH'):
                        for route in routes:
                                responses.append(requests.patch( self._libre_url + route, headers=self._header,json=request_data, verify = False))
        elif(self.functions[self._function_name]['request_method'] == 'POST'):
                        for route in routes:
                                responses.append(requests.post( self._libre_url + route, headers=self._header,json=request_data, verify = False))
        elif(self.functions[self._function_name]['request_method'] == 'PUT'):
                        for route in routes:
                                responses.append(requests.put( self._libre_url + route, headers=self._header, verify = False))

        call_output = []
        for response in responses:
                if response.status_code < 200 or response.status_code > 299: #Check for invalid HTTP response
                        if 'i' in self._flags : #if ignore error flag is enabled
                                continue
                        raise LibreNMSAPIClientException("API received invalid HTTP response %s" % response.text)
                if 'r' in self._flags:
                        call_output.append(response)
                else:
                        response_edata=json.loads(response.text) #Convert response to JSON object
                        if 'status' not in response_edata:
                                if 'i' in self._flags : #if ignore error flag is enabled
                                    continue
                                raise LibreNMSAPIClientException("API received invalid JSON response. %s" % response.text)
                        if response_edata['status'] != "ok":
                                if 'i' in self._flags : #if ignore error flag is enabled
                                    continue
                                raise LibreNMSAPIClientException("API received error response. %s" % response.text)
                        if 'e' in self._flags:
                                call_output.append(response_edata)
                        else:
                               if 'response_key' in self.functions[self._function_name]:
                                       if 'c'in self._flags:
                                               call_output = call_output + response_edata[self.functions[self._function_name]['response_key']]
                                       else:
                                               call_output.append(response_edata[self.functions[self._function_name]['response_key']])
                               elif 'message' in response_edata:
                                      call_output.append(response_edata['message'])
                               else:
                                     call_output.append(response_edata['status'])  

        if 'l' not in self._flags and len(call_output) == 1 :
                call_output=call_output[0]
                
        self._flags=''
        return call_output

    #Returns meta API Call function
    def __getattr__(self, function_name):
        function_name=function_name.lower()
        if function_name not in self.functions:
                sfunction_name=function_name.split('_',1) #Check for flags in function call
                if sfunction_name[1] in self.functions:
                        self._flags=sfunction_name[0]
                        function_name=sfunction_name[1]
                else:
                        raise LibreNMSAPIClientException("API Function '%s' does not exist" % function_name)
        self._function_name=function_name
        if 'flags' in self.functions[self._function_name]: #Check if function has required flags and concats them to existing flags.
                self._flags = self._flags + self.functions[self._function_name]['flags'] 
        return self._apicall
        
    def __init__(self, libre_url=None, api_token=None):
                self._flags=''
                if api_token is None and libre_url is None:
                        from dotenv import load_dotenv
                        load_dotenv()
                        api_token = os.environ['LibreNMS_APIToken']
                        self._libre_url = os.environ['LibreNMS_URL']
                else:
                        self._libre_url = libre_url
                self._header={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Auth-Token": api_token
                }
