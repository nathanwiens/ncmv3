import json
from ncmv3 import ncmv3

"""V3 API Key"""
api_key = "babwY0bNYqMwa0Kt0VTRknk6pqmOzNuz"

n3 = ncmv3.NcmClient(log_events=True)
n3.set_api_key(api_key)

"""Gets all users (up to page limit of 50)"""
# print(n3.get_users())

"""Gets all users (full list)"""
# print(n3.get_users(limit=0))

"""Gets all users, sorts by first name in reverse order"""
# print(n3.get_users(sort="-first_name"))

"""Gets all users, only returns first and last name"""
# print(n3.get_users(fields="first_name,last_name"))

"""Gets only a single user, returns just first name"""
# print(n3.get_users(email="user@domain.com", fields="first_name"))

"""Gets multiple users, returns just first and last name"""
# print(n3.get_users(email="user1@domain.com,user2@domain.com", fields="first_name,last_name"))

"""Searches for a user instead of filtering (works on partial match, not case-sensitive)"""
# print(n3.get_users(first_name="nat", search=True))

"""Changes the last name of a single user"""
# print(n3.update_user("user@domain.com", last_name="api"))

"""Deletes a user"""
# print(n3.delete_user("user@domain.com"))

"""Creates a new user with only the mandatory fields"""
# print(n3.create_user("user@domain.com", "API", "V3"))

"""Creates a new user, with account disabled (optional field)"""
# print(n3.create_user("user@domain.com", "API", "V3", is_active=False))

"""Gets all routers, returns only serial number"""
# print(n3.get_routers(fields="serial_number"))

"""Gets all subscriptions"""
# print(n3.get_subscriptions())

"""Gets all PCNs"""
# print(n3.get_private_cellular_networks())

"""Changes the Core IP of a PCN Network by name"""
# print(n3.update_private_cellular_network(name="NCMGNETWORK", core_ip="1.1.1.1"))

"""Creates a new Private Cellular Network"""
# print(n3.create_private_cellular_network("Test", "1.1.1.1"))

"""Deletes a Private Cellular Network"""
# print(n3.delete_private_cellular_network("01H7DNXG73NAZ3JXBPG15QQ96Z"))

"""Gets all Mobility Gateways"""
# print(n3.get_private_cellular_cores())

"""Gets all PCN SIMs"""
# print(n3.get_private_cellular_sims())

"""Changes the name of a PCN SIM"""
# print(n3.update_private_cellular_sim(id="89106120000000000665", name="SIM_89106120000000000665"))

"""Gets all Cellular APs"""
# print(n3.get_private_cellular_radios())

"""Changes the name of a Cellular AP"""
# print(n3.update_private_cellular_radio(id="01GPS8CBGRA23KMWPK368DCPFT", name="2210CW5000186"))
