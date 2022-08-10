# LibreNMSAPIClient
A Python API client library for (https://www.librenms.org/ "LibreNMS").  
LibreNMS is a fully featured network monitoring system that provides a wealth of features and device support.  

## Quick start
To begin import the API Client and create an instance of the LibreNMSAPIClient class. You can either hard code Libre's URL (without trailing / ) and API Token in the script, or rely on the .env file.

Once you have your API Client instance, you can begin calling Libre API functions directly as they appear in the Libre documentation. 

The parameter order is: dataobject (if function requires one), then the route parameters in the order that they're in the route then any additional Query parameters.

``` python
from LibreNMSAPIClient import LibreNMSAPIClient

# test =  LibreNMSAPIClient() # .env example
test =  LibreNMSAPIClient("http://YourLibreURL","api_token") # URL and Token hardcode example

testval=test.get_device("devicehostname")
print(testval)
```

# Advanced
You can input lists in the parameter fields and it will iterate through all possiblities for routes parameters. 

For Query parameters, all list entries will be applied to all.


## Function Flag  
You can append function flags to the beginning of functions followed by and underscore to adjust how the API behaves. 

{flags}_{function}({Parameters})

Flags:

i-ignore response errors. Responses are just dropped.

l-return response in list even if there's only one response/request.

e-entire response. Returns entire JSON object response.

r-raw response object that was received from requests. Skips all JSON conversion and most validation.

c-combines all of the API responses into a single list instead of a separate list for each response.

o-optional - makes all parameters optional.
