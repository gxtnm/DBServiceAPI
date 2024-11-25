import os
#import shutil
import requests
import base64
from typing import Optional, Dict

class AuthService:
    def __init__(self):
        self.jwt_token = None
        self.refresh_token = None
        self.client_id = "SupportClient"
        self.secret = "secret"
        self.basic_token = f"Basic {base64.b64encode(f'{self.client_id}:{self.secret}'.encode()).decode()}"
        self.username = 'un'
        self.first_basic_token = 'fbt'
        self.base_url = "https://oauth2.magticom.ge/auth/"  # Set this to your actual environment URL
        self.login_response = None    

    def get_base_url(self):
        return  self.base_url  
    
    def set_base_url(self,bas_url):
        self.base_url = bas_url

    def login(self, username: str, password: str) -> bool:
        self.removetokens()
        self.username = username

        # Define the data payload for login
        param_data = {
            'username': username,
            'password': password,
            'grant_type': 'two_factor_password'
        }

        headers = {
            'Authorization': self.basic_token
        }
        
        #print(f"self.basic_token : {self.basic_token}")
        response = requests.post(f"{self.base_url}oauth/token", data=param_data, headers=headers)
        self.login_response = response.json()
        
        if response.status_code == 200:
            tokens = response.json()
            self.set_basic_data(username, tokens.get("access_token"))            
            return True
        return False
    
    def get_login_response(self):
        return self.login_response 

    
    def removetokens(self):
        self.jwt_token = None
        self.refresh_token = None

    def logout(self):
        self.removetokens()
        print("Logged out and cleared all filters.")

    def revoke_token(self) -> bool:
        headers = {'Authorization': 'auth'}
        response = requests.post(f"{self.base_url}oauth/token/revoke", data={"access_token": self.jwt_token}, headers=headers)
        return response.status_code == 200

    def sms_verify(self, code: str) -> bool:
        param_data = {
            'grant_type': 'sms_code',
            'username': self.username,
            'smscode': code
        }
        headers = {'Authorization': self.basic_token}
        response = requests.post(f"{self.base_url}oauth/token", data=param_data, headers=headers)

        if response.status_code == 200:
            tokens = response.json()
            self.store_tokens(tokens.get("access_token"), tokens.get("refresh_token"))
            self.remove_basic_data()
            return True
        return False

    def sms_resend(self) -> bool:
        headers = {'Authorization': f"Bearer {self.first_basic_token}"}
        param_data = {'username': self.username}
        response = requests.post(f"{self.base_url}user/sms/send", data=param_data, headers=headers)
        return response.status_code == 200

    def refreshtoken(self) -> bool:
        param_data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        headers = {
            'Authorization': 'auth',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(f"{self.base_url}oauth/token", data=param_data, headers=headers)
        
        if response.status_code == 200:
            tokens = response.json()
            self.store_tokens(tokens.get("access_token"), tokens.get("refresh_token"))
            return True
        return False

    def set_basic_data(self, username: str, token: str):
        self.username = username
        self.first_basic_token = token

    def get_basic_data(self) -> Dict[str, Optional[str]]:
        return {
            "username": self.username,
            "bsToken": self.first_basic_token
        }

    def remove_basic_data(self):
        self.username = None
        self.first_basic_token = None

    def is_logged_in(self) -> bool:
        return self.basic_token is not None and self.username != 'un'

    def get_token(self) -> Optional[str]:
        return self.jwt_token

    def store_tokens(self, jwt: str, re_token: str):
        self.jwt_token = jwt
        self.refresh_token = re_token

    def store_restricted_token(self, jwt: str):
        self.jwt_token = jwt

    def get_response_type(self):
        return type(self.login_response)
