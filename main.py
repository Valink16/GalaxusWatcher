from unicodedata import category
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service

from time import sleep
import json
import util

o = webdriver.ChromeOptions()
o.add_argument("--log-level=3")
o.add_argument("--disable-blink-features=AutomationControlled")

s = Service(executable_path="chrome_win.exe")

driver = webdriver.Chrome(service=s, options=o)

watcher = util.Watcher(driver)

# urls = watcher.search("GTX", {"category": ["graphics cards"]})
# urls = watcher.search("phone", {"brand": ["samsung", "huawei"], "storage capacity": ["128 gb", "256 gb", "512 gb"], "price": "100-500"})
# urls = watcher.search("phone", {"brand": ["samsung", "huawei"], "storage capacity": ["32 gb"]})
# urls = watcher.search("RTX 3050", {"category": ["graphics cards"]})

# for url in urls:
# 	print(url)


creds = json.load(open("creds.json"))
watcher.watch(pushover_creds=creds)

input("Enter to close... ")
watcher.close()