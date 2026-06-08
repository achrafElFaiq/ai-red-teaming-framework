from okapi import get_okapi_token
from values import OKAPI_CLIENT_ID, OKAPI_CLIENT_SECRET, OKAPI_LITELLM_APP_SCOPE

print(get_okapi_token(OKAPI_CLIENT_ID, OKAPI_CLIENT_SECRET, OKAPI_LITELLM_APP_SCOPE))