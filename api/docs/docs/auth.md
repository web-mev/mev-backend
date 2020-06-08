## Authentication with MEV

Once a user is registered (with an email and password), requests to the API are controlled with a JWT contained in the request header.  Below is an example using Python's Requests library.  This example assumes you have created a user. 

First, exchange the username/password to get the API token:
```
import requests
token_url = 'http://127.0.0.1:8000/api/token/'
payload = {'email': '<EMAIL>', 'password': '<PASSWD>'}
token_response = requests.post(token_url, data=payload)
token_json = token_response.json()
```

Then, looking at `token_json`:
```
{'refresh': '<REFRESH TOKEN>', 'access': '<ACCESS_TOKEN>'}
```
We can then use that token in requests to the API:
```
access_token = token_json['access']
resource_list_url = 'http://127.0.0.1:8000/api/resources/'
headers = {'Authorization': 'Bearer %s' % access_token}
resource_response = requests.get(resource_list_url, headers=headers)
resource_json = resource_response.json()
```

If the token expires (a 401 response), you need to request a new token or refresh:
```
refresh_url = 'http://127.0.0.1:8000/api/token/refresh/'
payload = {'refresh': refresh_token}
refresh_response = requests.post(refresh_url, data=payload)
access_token = refresh_response.json()['access']
```
