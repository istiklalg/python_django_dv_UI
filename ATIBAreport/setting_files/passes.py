
# Email account information for production environment;
mail_production_address = 'mailadress@maildomain.com'
mail_production_password = 'mail_account_password'
email_production_host = ''
email_production_user = ''
email_production_pass = ''

# Database account information for production environment;
postgres_production_dbName = 'atibadb'
postgres_production_user = 'atibapg'
postgres_production_pass = 'Gsxr1100!'
postgres_production_host = '127.0.0.1'


postgresql_conn_string_dev = "dbname='atibadb' user='postgres' host='localhost' password='Zekeriya01'"
postgresql_conn_string_prod = f"dbname='{postgres_production_dbName}' user='{postgres_production_user}' host='127.0.0.1' password='{postgres_production_pass}'"


# For developing environment;
postgres_dbName = 'atibadb'

# 'HOST': '192.168.1.62',
# 'HOST': '127.0.0.1',

# keys from Fernet()
# encription_key = "b'GIZQcyWrp0vbiYEmYWFmFe9NBxdNiJg9xtd2dO6UPIk='"
# encription_key = 'GIZQcyWrp0vbiYEmYWFmFe9NBxdNiJg9xtd2dO6UPIk='

# keys for us
# encription_key = b'\xe9\x917$\xeb%?\xb0\xe1\xf8\xb3\x037\x8d2Kn\xd2\xb8akU\x9dm\xdaj\x99\x1c\xc3\xd7A\xc5'
# encription_key = base64.b64decode('6ZE3JOslP7Dh+LMDN40yS27SuGFrVZ1t2mqZHMPXQcU=')
encription_key = '6ZE3JOslP7Dh+LMDN40yS27SuGFrVZ1t2mqZHMPXQcU='


# atibaApiService necessities   :
atibaApiService_PORT = 23269
atibaApiService_API_KEY = "S3V0SGFzQ2Vua0t1ckZhdGw2atM1Tgun1bwCEECThOs="

