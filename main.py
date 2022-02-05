from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service

from time import sleep
import json
import urllib
from http.client import HTTPSConnection
import util

o = webdriver.ChromeOptions()
o.add_argument("--log-level=3")
o.add_argument("--disable-blink-features=AutomationControlled")

s = Service(executable_path="chrome_win.exe")

# urls = watcher.search("GTX", {"category": ["graphics cards"]})
# urls = watcher.search("phone", {"brand": ["samsung", "huawei"], "storage capacity": ["128 gb", "256 gb", "512 gb"], "price": "100-500"})
# urls = watcher.search("phone", {"brand": ["samsung", "huawei"], "storage capacity": ["32 gb"]})
# urls = watcher.search("RTX 3050", {"category": ["graphics cards"]})

# for url in urls:
# 	print(url)


creds = json.load(open("creds.json"))
# creds = None

galaxus_creds = json.load(open("galaxus_creds.json"))

while True:
	try:
		driver = webdriver.Chrome(service=s, options=o)
		watcher = util.Watcher(driver)
		watcher.watch(pushover_creds=creds, delay=60)
	except KeyboardInterrupt:
		exit()
	except Exception as e:
		print("Error occured, {}, restarting now...".format(e))
		pushover_conn = HTTPSConnection("api.pushover.net:443")
		pushover_conn.request("POST", "/1/messages.json",
			urllib.parse.urlencode({
				"token": creds["token"],
				"user": creds["user"],
				"title": "GalaxusWatcher",
				"message": "Error occured, restarting",
				"priority": 2,
				"retry": 30,
				"expire": 300
			})
		)
		res = pushover_conn.getresponse().read()
		continue
