from faulthandler import is_enabled
from math import prod
from operator import is_not
from time import sleep
from typing import List
from attrs import exceptions
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

WAIT_TIMEOUT = 5

class Watcher:
	"""
	Class wrapping functionality to scrape data from the Galaxus website
	"""
	def __init__(self, driver):
		self.base_url = "https://www.galaxus.ch/"
		self.language = "en/"
		self.driver = driver

	def search(self, term: str, filters: dict, take=20) -> List[str]:
		"""
		Searches for a product name, with filtering and sorting applied
		Returns list of URLs of matches
		"""
		self.driver.get(self.base_url + self.language + "search?q={}".format(term))

		self.apply_filters(filters)

		self.driver.get(self.driver.current_url + "&take={}".format(take))

		# Wait till the products are loaded
		WebDriverWait(self.driver, 10) \
			.until(
				EC.presence_of_element_located((
					By.CSS_SELECTOR, 
					".panelProduct > a"
				))
			)
			
		return list(map(
			lambda product: product.get_attribute("href"),
			self.driver.find_elements(By.CSS_SELECTOR, ".panelProduct > a")
		))

	def apply_filters(self, filters: dict):
		"""
		Applies the given filters to the current page, panics if no filters available, all values should be lower case
		Filters should be a dict containing string keys with the filter name and lists containing the wanted values for the given filter
		"""
		# Expand all filters
		try:
			filters_button = WebDriverWait(self.driver, WAIT_TIMEOUT) \
				.until(
					EC.presence_of_element_located((
						By.XPATH, 
						"//div[@id=\"productListingContainer\"]//div//div//div//button[text()=\"More filters\"]"
					))
				)
			filters_button.click()
		except TimeoutException:
			pass

		for k in filters:
			nav = WebDriverWait(self.driver, WAIT_TIMEOUT) \
				.until(
					EC.visibility_of_element_located((
						By.CSS_SELECTOR, 
						"div[role=\"navigation\"]"
					))
				)
			
			# collect all filters
			filter_buttons = nav.find_elements(By.CSS_SELECTOR, "div > div > button > div > div:nth-child(1)")[:-1] # Exclude last, which is the "Fewer filters" button
			filter_keys = list(map(lambda elem: elem.text.lower(), filter_buttons))

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
				for box in filter_table_boxes:
					if box.get_attribute("title").lower() in filters[k]: # Check the box if it's wanted
						box.click()
				
				filter_table.find_element(By.CSS_SELECTOR, "button[title=\"Close\"]").click()
			except ValueError:
				pass # The provided filter is simply not applicable


	def close(self):
		self.driver.close()
