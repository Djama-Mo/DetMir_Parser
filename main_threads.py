import csv
import time
from collections import namedtuple
from selenium import webdriver
import selenium.common.exceptions
from bs4 import BeautifulSoup as bs
import lxml
import threading


URL = 'https://www.detmir.ru/catalog/index/name/zdorovyj_perekus_pp/'
SPB = '/html/body/div[4]/div[4]/div/div/div[2]/div/div[2]/div/ul/li[16]/ul/li[2]'
MSK = '/html/body/div[5]/div[4]/div/div/div[2]/div/div[2]/div/ul/l qi[11]/ul/li[1]'
MORE = '//*[@id="app-container"]/div[2]/header/div/div[2]/div/div/div[1]/ul/li[2]/div/div/div[1]/div[1]'
MORE_PRODUCTS = '//*[@id="app-container"]/div[2]/div[1]/main/div/div[2]/div[2]/div/div[2]/div/div/button'
Result = namedtuple('Result',
                    ('ID', 'Title', 'Price', 'City', 'Old_price', 'URL'))

HEADERS = (
    'ID товара',
    'Наименование',
    'Цена',
    'Город',
    'Промо цена',
    'Ссылка'
)

options = webdriver.ChromeOptions()
options.add_argument('disable-notifications')
options.add_argument('--headless')


def dec_time(func):
    def check_time(*args):
        _start = time.time()
        result = func(*args)
        _end = time.time()
        print(f'{func.__name__} ---------- Total time', _end - _start)
        return result

    return check_time


def product_xpath(idx):
    return f'/html/body/div[3]/div[2]/div[1]/' \
           f'main/div/div[2]/div[2]/div/div[1]/' \
           f'div/div[4]/div/div/div/div[{idx}]'


def choose_city(driver, city):
    driver.find_element_by_xpath(MORE).click()
    driver.find_element_by_xpath('//*[@id="app-container"]/div[2]/header/'
                                 'div/div[2]/div/div/div[1]/ul/li[2]/div/'
                                 'div/div[1]/div[2]/div/div/ul/li[1]').click()
    time.sleep(1)
    driver.find_element_by_xpath(city).click()


class Parser(threading.Thread):
    def __init__(self, region=MSK, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = webdriver.Chrome(options=options)
        self.city = ''
        self.region = region
        self.result = []

    def save_result(self, spb=0):
        with open('results.csv', 'a+') as fl:
            writer = csv.writer(fl, quoting=csv.QUOTE_MINIMAL)
            if not spb:
                writer.writerow(HEADERS)
            for item in self.result:
                writer.writerow(item)

    def get_city(self):
        city = self.driver.find_element_by_xpath('//*[@id="app-container"]/div[2]/header/'
                                                 'div/div[2]/div/div/div[1]/ul/li[2]/'
                                                 'div/div/div[1]/div[2]/div/div/ul/li[1]/'
                                                 'div/div[1]/div/span').get_attribute('innerHTML')
        return city

    def get_main_info(self, element, city):
        soup = bs(element, 'lxml')
        frame = soup.select('p')
        item_sale = ''
        if len(frame) > 2:
            item_title, item_sale, item_price = frame
            item_sale = item_sale.get_text().replace(u'\xa0', u' ')
        else:
            item_title, item_price = frame
        item_title = item_title.get_text()
        item_price = item_price.get_text().replace(u'\xa0', u' ')
        item_url = soup.select_one('a').get('href')
        item_id = ''.join(filter(lambda character: character.isdigit(), item_url))
        self.result.append(Result(
            ID=item_id,
            Title=item_title,
            Price=item_price,
            City=city,
            Old_price=item_sale,
            URL=item_url
        ))

    def clickMore(self, i=0):
        while i < 12:
            self.driver.find_element_by_xpath(MORE_PRODUCTS).click()
            time.sleep(0.1)
            i += 1
        return i

    def run(self):
        self.driver.get(URL)
        spb_flag = 0
        if self.region != MSK:
            spb_flag = 1
            choose_city(self.driver, self.region)
        time.sleep(1.5)
        city = self.get_city()
        i = 0
        try:
            time.sleep(1)
            while i < 20:
                self.driver.find_element_by_xpath(MORE_PRODUCTS).click()
                time.sleep(0.5)
                i += 1
        except selenium.common.exceptions.ElementClickInterceptedException:
            if i < 19:
                try:
                    self.clickMore()
                except selenium.common.exceptions.ElementClickInterceptedException:
                    pass
        for idx in range(1, 510):
            _product_xpath = product_xpath(idx)
            element = self.driver.find_element_by_xpath(_product_xpath).get_attribute('innerHTML')
            self.get_main_info(element, city)
        self.save_result(spb_flag)


@dec_time
def main():
    parsers = [Parser(), Parser(SPB)]
    for parser in parsers:
        parser.start()
    for parser in parsers:
        parser.join()
    for parser in parsers:
        parser.driver.close()
    return


if __name__ == '__main__':
    main()
