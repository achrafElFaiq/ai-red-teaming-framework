import requests
import values
import json
import base64
from jwt.algorithms import ECAlgorithm
import jwt

def get_okapi_token(client_id, client_secret, scope):
    response = requests.post(
      url=values.OKAPI_URL,
        data={
            "grant_type": "client_credentials",
            "scope": scope
         },
        auth=requests.auth.HTTPBasicAuth(client_id, client_secret)
    )
    # print(response.json())
    return response.json()["access_token"]

## Fonction utilitaire

def get_public_key(kid):
    public_keys = requests.get(values.PUBLIC_KEY_URL).json()["keys"]
    public_key = list(filter(lambda key_obj: key_obj["kid"] == kid, public_keys))[0]
    return ECAlgorithm.from_jwk(public_key)

def get_header(token: str):
    return json.loads(base64.b64decode(token.split(".")[0]+'==').decode("utf-8"))

def get_body(token: str):
    return json.loads(base64.b64decode(token.split(".")[1]+'==').decode("utf-8"))

def get_signature(public_key: str, options: dict[str: str], token: str):
    return jwt.decode(
        algorithms=values.ALGORITHMS,
        jwt=token,
        key=public_key,
        options=options
    )