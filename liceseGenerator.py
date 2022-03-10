
"""
@author: istiklal
"""
import json
import os
from datetime import datetime
import base64
from Cryptodome.Cipher import AES


class AESCipher:
    def __init__(self):
        self.key = base64.b64decode('6ZE3JOslP7Dh+LMDN40yS27SuGFrVZ1t2mqZHMPXQcU=')

    def encrypt(self, raw):
        # print("key : ", self.key)
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


if __name__ == "__main__":
    # lic = {
    #     "atiba-license": {"customer_name": "Hacettepe Universitesi",
    #                       "customer_email": "sadik.toklu@hacettepe.edu.tr",
    #                       "customer_country": "Turkey",
    #                       "customer_city": "Ankara",
    #                       "customer_contact_number": "+903122976200",
    #                       "customer_po": "PO-20210413-01",
    #                       "license_type": "temporary",  # "temporary" for demo, "permanent" for commercial products
    #                       "product_sku": [
    #                           {"licname": "AL", "licdevtype": "NETW", "liccount": 2000},
    #                           {"licname": "AL", "licdevtype": "WL", "liccount": 2000}],
    #                       "exp_date": "13-07-2021",
    #                       # "hw_mac_address": "63d206968d4532a1283c4480dcc6ff15ea1103ba937329d2f5bb5d47c8116687"
    #                       # "hw_mac_address": "e1e0b7cd240ffd9e5db1500597fcbf96a661559d8b7409a7afdc5c26275bc931"
    #                       "hw_mac_address": "a6a35a0609b353aa4734450c2761ac2ac8bec5a3ae054eec905eb975644b9c48"
    #                       }
    # }
    #
    # lic = json.dumps(lic)
    # print(type(lic))
    # print(lic)
    # cipher = AESCipher()
    # encrypted_text = cipher.encrypt(lic)
    # print(encrypted_text)
    # decrypted_text = cipher.decrypt(encrypted_text)
    # print(decrypted_text)
    # dec_json = json.loads(decrypted_text)
    # print(dec_json)
    # print(dec_json["atiba-license"]["exp_date"])
    # print(dec_json["atiba-license"]["license_type"])

    """
    -------------------------------------------------------------------------------------------------------------------
    """

    hw_mac_address = input("The Unique String Given From ATIBA UI : ")
    customer_name = input("Customer Name : ")
    customer_email = input("Customer Email Address : ")
    customer_country = input("Customer Country (Which country is the customer located) : ")
    customer_city = input("Customer City (Which country is the customer located) : ")
    customer_contact_number = input("Customer Contact Number : ")
    customer_po = input("Purchase Order (Give like PO-20210527-01) : ")
    license_type = input("License Type (Write 'temporary' or 'permanent') : ")
    exp_date = input("Expiration Date of License (Give like 13-10-2021) : ")

    licdevtype_list = ["WL", "WEBS", "WEBG", "WANA", "NETW", "STOR", "SRV", "SEC", "ROTR", "SPRE", "DB", "APPS", "AP"]
    product_sku = []
    _process = True if license_type != "temporary" else False

    print(f"Give product details for ATIBA LOG (AL) license")
    print(f"Device type codes : ")
    print(f"                    Wireless Controller : WL")
    print(f"                    Web Service : WEBS")
    print(f"                    Web Gateway : WEBG")
    print(f"                    WAN Accelerator : WANA")
    print(f"                    Switch : NETW")
    print(f"                    Storage : STOR")
    print(f"                    Server : SRV")
    print(f"                    Security : SEC")
    print(f"                    Router : ROTR")
    print(f"                    Server Premium : SPRE")
    print(f"                    Database : DB")
    print(f"                    App Service : APPS")
    print(f"                    Access Point : AP")
    print(f"When it's over enter 0")

    while _process:
        licdevtype = input("Give device type code : ")
        if licdevtype not in licdevtype_list:
            print(f"Please enter a valid device type code !! '{licdevtype}' is not in {licdevtype_list}")
            continue

        liccount = input(f"Give count for {licdevtype} : ")
        try:
            liccount = int(liccount)
        except:
            print(f"Count must be integer, i guess you know that !!!!")
            continue
        product_sku.append({"licname": "AL", "licdevtype": licdevtype, "liccount": liccount})
        print(f"Added {len(product_sku)} product details like this for now : {product_sku}")
        licdevtype_list.remove(licdevtype)
        _continue = input(f"-------------------------------> Continue? (press any key to continue, 0 to finish) ? : ")
        _process = False if _continue == "0" else True

    if license_type != "temporary":
        for code in licdevtype_list:
            product_sku.append({"licname": "AL", "licdevtype": code, "liccount": 0})

    lic = {
        "atiba-license": {"customer_name": customer_name,
                          "customer_email": customer_email,
                          "customer_country": customer_country,
                          "customer_city": customer_city,
                          "customer_contact_number": customer_contact_number,
                          "customer_po": customer_po,
                          "license_type": license_type,  # "temporary" for demo, "permanent" for commercial products
                          "product_codes": ["AL"],
                          # "product_sku": [
                          #     {"licname": "AL", "licdevtype": "NETW", "liccount": 2000},
                          #     {"licname": "AL", "licdevtype": "WL", "liccount": 2000}],
                          "product_sku": product_sku,
                          "exp_date": exp_date,
                          "hw_mac_address": hw_mac_address
                          }
    }

    lic = json.dumps(lic)
    # print(type(lic))
    print("  ")
    print(" ******** ")
    print("License Details : ")
    print("          ", lic)
    print(" ******** ")
    cipher = AESCipher()
    encrypted_text = cipher.encrypt(lic)
    print("Your License Key : ")
    print("          ", encrypted_text)
    print(" ******** ")
    # decrypted_text = cipher.decrypt(encrypted_text)
    # print(decrypted_text)
    # dec_json = json.loads(decrypted_text)
    # print(dec_json)
    # print(dec_json["atiba-license"]["exp_date"])
    # print(dec_json["atiba-license"]["license_type"])