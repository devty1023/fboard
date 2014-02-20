import requests
import json
import _config as cf

payload = { 'access_token': cf.APP_ID+'|'+cf.APP_SECRET }
r = requests.request('GET', 'https://graph.facebook.com/174499879257223/feed', params=payload)
data =  json.loads(r.content)['data']
#print data


r = requests.request('GET', 'https://graph.facebook.com/1015636459/picture')
print r.url


