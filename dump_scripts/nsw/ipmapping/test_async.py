import grequests

urls = ["https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER=CZ242401KN", 
        "https://sapwebdisp01.cz.foxconn.com:4300/orion/polaris/ssn_mac_pwd_license?SERIAL_NUMBER=CZ242401KM"]

def do_something(response):
    print(response.url, response)

async_list = []

for url in urls:
    action = grequests.get(url, hooks = {'response': do_something})

    async_list.append(action)

grequests.map(async_list)