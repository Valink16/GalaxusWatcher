from email import message
from gc import collect
from re import T
from time import sleep
from typing import List, Tuple
from http.client import HTTPSConnection
import urllib
import threading
import datetime
import json
import webbrowser
import winsound

import flask

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

import bs4 as bs

WAIT_TIMEOUT = 5

class UnavailableFilterChoice(Exception):
	pass

class Watcher:
	"""
	Class wrapping functionality to scrape data from the Galaxus website
	"""
	def __init__(self, driver):
		self.base_url = "https://www.galaxus.ch/"
		self.language = "en/"
		self.checkout = "checkout/"
		self.driver = driver

	def search(self, term: str, filters: dict, take=20) -> List[dict]:
		"""
		Searches for a product name, with filtering and sorting applied
		Returns list of URLs of matches
		"""
		self.driver.execute_script('alert("Focus window")')
		
		self.driver.switch_to.alert.accept()

		self.driver.get(self.base_url + self.language + "search?q={}".format(term))

		try:
			self.apply_filters(filters)
		except UnavailableFilterChoice:
			return []

		self.driver.get(self.driver.current_url + "&take={}".format(take))

		# print("Waiting for products to load...")
		# Wait till the products are loaded
		WebDriverWait(self.driver, 10) \
			.until(
				EC.presence_of_element_located((
					By.CSS_SELECTOR, 
					".panelProduct"
				))
			)
			
		def mapf(product):
			# print(bs.BeautifulSoup(product.get_attribute("innerHTML")).prettify())
			# print(product.get_attribute("outerHTML"))
			ac = ActionChains(self.driver)
			ac.move_to_element(product.find_element(By.CSS_SELECTOR, "div > div > span"))
			ac.perform()
			
			popup = WebDriverWait(self.driver, WAIT_TIMEOUT) \
				.until(EC.visibility_of_element_located((
					By.CSS_SELECTOR,
					"div[data-test=\"popover\"]"
				)))

			delivery_options = {}
			

			options_names = popup.find_elements(By.XPATH, "./div[2]/h3")
			option_texts = popup.find_elements(By.XPATH, "./div[2]/span/div")

			if len(option_texts) < len(options_names):
				option_texts.append(None)

			for option_name, option_text in zip(options_names, option_texts):
				text = option_text.text if option_text else "OK"
				delivery_options[option_name.text.lower()] = text.lower().replace('\n', ' ')
			
			# print(delivery_options)

			popup.find_element(By.CSS_SELECTOR, "button").click()
			
			a = product.find_element(By.XPATH, "./a")
			return {
				"name": a.get_attribute("aria-label"),
				"href": a.get_attribute("href"),
				"price": product.find_element(By.CSS_SELECTOR, "span > strong").text,
				"availability": delivery_options
			}
		
		products = self.driver.find_elements(By.CSS_SELECTOR, ".panelProduct")
		return list(map(mapf, products))

	def collect_filter_buttons(self):
		# Expand all filters
		expanded_filters = False
		try:
			
			filters_button = WebDriverWait(self.driver, 1) \
				.until(
					EC.presence_of_element_located((
						By.XPATH, 
						"//div[@id=\"productListingContainer\"]//div//div//div//button[text()=\"More filters\"]"
					))
				)
			filters_button.click()
			expanded_filters = True
		except TimeoutException:
			pass
		
		nav = WebDriverWait(self.driver, WAIT_TIMEOUT) \
			.until(
				EC.visibility_of_element_located((
					By.CSS_SELECTOR, 
					"div[role=\"navigation\"]"
				))
			)
		
		# collect all filters
		if expanded_filters:
			filter_buttons = nav.find_elements(By.CSS_SELECTOR, "div > div > button > div > div:nth-child(1)")[:-1] # Exclude last, which is the "Fewer filters" button
		else:
			filter_buttons = nav.find_elements(By.CSS_SELECTOR, "div > div > button > div > div:nth-child(1)")
		
		filter_keys = list(map(lambda elem: elem.text.lower(), filter_buttons))

		return (filter_buttons, filter_keys)

	def apply_filters(self, filters: dict):
		"""
		Applies the given filters to the current page, panics if no filters available, all values should be lower case
		Filters should be a dict containing string keys with the filter name and lists containing the wanted values for the given filter
		the price key is in format: "%d-%d"
		"""

		filter_buttons, filter_keys = self.collect_filter_buttons()
		if "price" in filters:
			try:
				i = filter_keys.index("price")
				filter_buttons[i].click()

				# Wait until the selection menu opens
				WebDriverWait(self.driver, WAIT_TIMEOUT) \
					.until(
						EC.visibility_of_element_located((
							By.CSS_SELECTOR,
							"input[inputmode=\"decimal\"]"
						))
					)

				min, max = self.driver.find_elements(By.CSS_SELECTOR, "input[inputmode=\"decimal\"]")

				min.send_keys(Keys.CONTROL + "a")
				min.send_keys(filters["price"].split('-')[0])
				max.send_keys(Keys.CONTROL + "a")
				max.send_keys(filters["price"].split('-')[1])

				try:
					self.driver.find_element(By.XPATH, "//button[contains(text(),\"products\")]").click()
				except NoSuchElementException:
					self.driver.find_element(By.XPATH, "//button[contains(text(),\"Close\")]").click()

				filters.pop("price")
			except ValueError:
				pass

		for k in filters:
			# collect all filters
			# print(k)
			filter_buttons, filter_keys = self.collect_filter_buttons()
	
			try:
				j = filter_keys.index(k) # Index of our applicable filter
			
				filter_buttons[j].click() # Click on filter button to select value

				# Wait until the selection menu opens
				filter_table = WebDriverWait(self.driver, WAIT_TIMEOUT) \
					.until(
						EC.presence_of_element_located((
							By.CSS_SELECTOR,
							"div[tabindex]"
						))
					)

				filter_table_boxes = filter_table.find_elements(By.CSS_SELECTOR, "div[role=\"checkbox\"]")
				filter_table_boxes_values = list(map(lambda b: b.get_attribute("title").lower(), filter_table_boxes))

				for i, value in enumerate(filters[k]):
					try:
						filter_table_boxes[filter_table_boxes_values.index(value)].click()
					except ValueError:
						# print("{} not available".format(value))
						filter_table.find_element(By.CSS_SELECTOR, "button[title=\"Close\"]").click()
						raise UnavailableFilterChoice

				# for box in filter_table_boxes:
				# 	if box.get_attribute("title").lower() in filters[k]: # Check the box if it's wanted
				# 		box.click()
				
				filter_table.find_element(By.CSS_SELECTOR, "button[title=\"Close\"]").click()
			except ValueError:
				# print("{} not applicable...".format(k))
				pass # The provided filter is simply not applicable

	def watch(self, watchlist="watchlist.json", pushover_creds=None, take=20, delay=60):
		watchlist = json.load(open(watchlist))
		urls = []
		last_len = len(urls)
		last_update_time = datetime.time()
		pushover_conn = HTTPSConnection("api.pushover.net:443") if pushover_creds is not None else None

		web_serv = flask.Flask("GalaxusWatcher")

		@web_serv.route("/hello/")
		def hello():
			return """<!DOCTYPE html>
<html>
<body>

<h2>An Unordered HTML List</h2>

<ul>
  <li>Coffee</li>
  <li>Tea</li>
  <li>Milk</li>
</ul>  

<h2>An Ordered HTML List</h2>

<ol>
  <li>Coffee</li>
  <li>Tea</li>
  <li>Milk</li>
</ol> 

</body>
</html>
"""

		@web_serv.route("/")
		def show_urls():
			page = """<head>
	<link rel="stylesheet" href="static/style.css">
	<meta http-equiv="refresh" content="60">
</head><body><table> <tr> <th>Products</th> <th>Price</th> <th>Collection</th> </tr>
			"""
			for u in urls:
				# print(u["name"])
				try:
					collection_status = None
					if "collection" in u["availability"]:
						collection_status = "Unavailable" if "collection not available" in u["availability"]["collection"] else "Available"
					elif "shipping / collection" in u["availability"]:
						collection_status = "Available"
					else:
						collection_status = "Unavailable"

					page += "<tr> <td> <a href={}>{}</a> </td> <td> {} </td> <td>{}</td> </tr>".format(u["href"], u["name"], u["price"], collection_status)
				except KeyError:
					print(u)
			page += "</table>"
			page += "<p>Last updated at {}</p>".format(last_update_time.strftime("%H:%M:%S"))
			page += "</body>"
			return page

		@web_serv.route("/staiic/<path:path>")
		def serve_static(path):
			return flask.send_from_directory("static", path)


		f = threading.Thread(target=web_serv.run, kwargs={"host": "0.0.0.0", "port": 443, "ssl_context": "adhoc"})
		f.setDaemon(True)
		f.start()
		
		init = False
		while True:
			for item in watchlist:
				last_update_time = datetime.datetime.now()
				print("Last updated at {}".format(last_update_time.strftime("%H:%M:%S")))
				new_urls = self.search(item["term"], item["filters"], take=take)
				future_urls = []
				for nu in new_urls:
					if not nu in urls:
						webbrowser.open(nu["href"])
						message = "New product available: {}, {}".format(nu["name"], nu["price"])
						future_urls.append(nu)
						
						print(message)
						if (pushover_conn is not None) and init: # To do not spam the user on init
							self.alert(pushover_conn, pushover_creds, {
								"token": pushover_creds["token"],
								"user": pushover_creds["user"],
								"title": "GalaxusWatcher",
								"message": message,
								"url_title": "Product link",
								"url": nu["href"],
								"priority": 2,
								"retry": 30,
								"expire": 300
							}, beep=True)
				
				if pushover_conn is not None and not init:
					self.alert(pushover_conn, pushover_creds, {
						"token": pushover_creds["token"],
						"user": pushover_creds["user"],
						"title": "GalaxusWatcher",
						"message": "Products available: {}".format(len(future_urls)),
					})

				urls += future_urls
				init = True

				for u in urls:
					if not u in new_urls:
						print("A product has disappeared: {}, {}".format(u["name"], u["price"]))
						urls.remove(u)


			if not len(urls) == last_len:
				last_len = len(urls)
				print("Currenty {} products available".format(last_len))
			
			remaining = delay - (datetime.datetime.now() - last_update_time).total_seconds()
			if remaining > 0:
				sleep(remaining)

	def login(self, creds):
		self.driver.get("https://id.digitecgalaxus.ch/login")

		email = WebDriverWait(self.driver, WAIT_TIMEOUT) \
			.until(
				EC.presence_of_element_located((
					By.CSS_SELECTOR,
					"input[type=\"email\"]"
				))
			)

		password = self.driver.find_element(By.CSS_SELECTOR, "input[type=\"password\"]")
		login_button = self.driver.find_element(By.CSS_SELECTOR, "button[value=\"login\"]")
		
		ac = ActionChains(self.driver)
		ac.move_to_element(email)
		ac.click()
		ac.pause(1)
		for c in creds["email"]:
			ac.send_keys(c)
			ac.pause(0.5)
		ac.pause(1)
		ac.move_to_element(password)
		ac.click()
		ac.pause(1)
		for c in creds["password"]:
			ac.send_keys(c)
			ac.pause(0.5)
		ac.pause(1)
		ac.move_to_element(login_button)
		ac.pause(1)
		ac.click()

		ac.perform()

	def purchase(self, url, creds):
		self.driver.get(url)

		add_to_basket_button = WebDriverWait(self.driver, WAIT_TIMEOUT) \
			.until(
				EC.presence_of_element_located((
					By.CSS_SELECTOR,
					"button[id=\"addToCartButton\"]"
				))
			)

		add_to_basket_button.click()

		WebDriverWait(self.driver, WAIT_TIMEOUT) \
			.until(
				EC.presence_of_element_located((
					By.CSS_SELECTOR,
					"div[data-test=\"upsellingContentHeader\"]"
				))
			)
		
		self.driver.get(self.base_url + self.language + self.checkout)

		email = WebDriverWait(self.driver, WAIT_TIMEOUT) \
			.until(
				EC.presence_of_element_located((
					By.CSS_SELECTOR,
					"input[type=\"email\"]"
				))
			)

		password = self.driver.find_element(By.CSS_SELECTOR, "input[type=\"password\"]")
		login_button = self.driver.find_element(By.CSS_SELECTOR, "button[value=\"login\"]")
		
		ac = ActionChains(self.driver)
		ac.move_to_element(email)
		ac.click()
		ac.pause(1)
		for c in creds["email"]:
			ac.send_keys(c)
			ac.pause(0.5)
		ac.pause(1)
		ac.move_to_element(password)
		ac.click()
		ac.pause(1)
		for c in creds["password"]:
			ac.send_keys(c)
			ac.pause(0.5)
		ac.pause(1)
		ac.move_to_element(login_button)
		ac.pause(1)
		ac.click()

		ac.perform()

	def alert(self, conn, creds, msg, beep=False):
		if beep:
			def beep():
				for i in range(5):
					winsound.Beep(1000, 500)

			thread = threading.Thread(target=beep)
			thread.start()

		conn.request("POST", "/1/messages.json",
			urllib.parse.urlencode(msg)
		)
		res = conn.getresponse()
		if not res.status == 200:
			print("Failed to push notification", bs.BeautifulSoup(res.read()).beautify())
		else:
			res.read()

	def close(self):
		self.driver.close()
