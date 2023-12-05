import os
import json

listen_addr = os.environ.get('listen_addr', '0.0.0.0')

USERS = os.environ.get('USERS', '').split('#')
PASS = os.environ.get('PASS', '').split('#')
MOUNT_POINTS = os.environ.get('MOUNT_POINTS', '').split('#')

users_str = str(USERS)

try:
    listen_port = int(os.environ.get('listen_port', '2101'))
    max_client =  int(os.environ.get('max_client', '4'))
    max_source = int(os.environ.get('max_source', '4'))
    max_pending = int(os.environ.get('max_pending', '10'))
except ValueError:
    raise Exception('listen_port, max_client, max_source and max_pending must be integer')




try:
    assert len(USERS) == len(PASS) == len(MOUNT_POINTS)
    
except AssertionError:
    raise Exception('USERS, PASSWORDS and MOUNT_POINTS must have the same length and be separated by # symbol and at least one must be provided')


tokens_client = {}
for index, user in enumerate(USERS):
    tokens_client.update({ f'{USERS[index]}:{PASS[index]}': MOUNT_POINTS[index]})
    
print(tokens_client)


tokens_source = {}
for index, user in enumerate(USERS):
    tokens_source.update({PASS[index]: MOUNT_POINTS[index]})

print(tokens_source)

dict_config = { 'listen_addr': listen_addr,
                'listen_port': listen_port,
                'max_client': max_client,
                'max_source': max_source,
                'max_pending': max_pending,
                'tokens_client': tokens_client,
                'tokens_source': tokens_source,
                }

with open('ok.json', 'w') as f:
    json.dump(dict_config, f, indent=4)