import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service


from time import sleep

s = Service("gecko_win.exe")

driver = webdriver.Firefox(service=s)
driver.get("https://google.com")


driver.close()