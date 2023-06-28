from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

c_max_weight = {'FOOT': 10, 'BIKE': 20, 'AUTO': 40}
c_max_orders = {'FOOT': 2, 'BIKE': 4, 'AUTO': 7}
c_max_regions = {'FOOT': 1, 'BIKE': 2, 'AUTO': 3}
c_first_order_dur = {'FOOT': 25, 'BIKE': 12, 'AUTO': 8}
c_other_orders_dur = {'FOOT': 10, 'BIKE': 8, 'AUTO': 4}
courier_types = ['FOOT', 'BIKE', 'AUTO']
c_earning_rates = {'FOOT': 2, 'BIKE': 3, 'AUTO': 4}
c_rating_rates = {'FOOT': 3, 'BIKE': 2, 'AUTO': 1}
