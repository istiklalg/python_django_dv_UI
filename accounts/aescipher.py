# -*- coding: utf-8 -*-
"""
Created on Mon Mar 15 17:25:55 2021

@author: Kutay
"""
import base64
from Cryptodome.Cipher import AES


class AESCipher:
    def __init__(self):
        self.key = base64.b64decode('6ZE3JOslP7Dh+LMDN40yS27SuGFrVZ1t2mqZHMPXQcU=')

    def encrypt(self, raw):
        print("key : ", self.key)
        BS = 16
        pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
        raw = pad(raw)
        iv = "KutHasCenkKurFat".encode('UTF-8')
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw.encode())).decode()

    def decrypt(self, enc):
        unpad = lambda s: s[:-ord(s[len(s) - 1:])]
        enc = base64.b64decode(enc)
        iv = "KutHasCenkKurFat".encode('UTF-8')
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc[16:])).decode()