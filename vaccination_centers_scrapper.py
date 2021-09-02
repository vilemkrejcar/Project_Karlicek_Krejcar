import mechanicalsoup
import requests
import copy
import pandas as pd
from bs4 import BeautifulSoup
from time import sleep
from config import URL_VACCENTERS, REGIONS, CENTER_TYPE, VACCINES, CSV_VACCENTERS, ADRESA2GPS
from data_structures import VaccCenter

class VaccCentersScraper():
    url = URL_VACCENTERS

    def __init__(self, regions=REGIONS):
        self.regions = regions
        self.vacc_centers = []

    def get_links(self):
        browser = mechanicalsoup.StatefulBrowser(raise_on_404=True)
        for reg in self.regions:
            browser.open(self.url)
            form = browser.select_form('form[id=filter]')
            form['FilteredByRegion'] = reg
            response = browser.submit_selected()
            self._extract_links_from_soup(BeautifulSoup(response.text.strip()), reg)
            sleep(1)
        browser.close()
        return None

    def get_information_about_centers(self):
        for center in self.vacc_centers:
            soup = BeautifulSoup(requests.get(center.link).text.strip())
            center.add_info(self._extract_info_from_soup(soup))
            center.add_open_hours(self._extract_open_hours_from_soup(soup))
            center.add_vaccines(self._extract_vaccines(center.info))
            sleep(0.5)
        return None

    def get_gps_of_centers(self):
        data = pd.read_csv(CSV_VACCENTERS)[['ockovaci_misto_id', 'latitude', 'longitude']].set_index('ockovaci_misto_id')
        vacc_ids = set(data.index)
        no_data = []
        for i in range(len(self.vacc_centers)):
            if self.vacc_centers[i].vacc_id in vacc_ids:
                gps = tuple(data.loc[self.vacc_centers[i].vacc_id])
                self.vacc_centers[i].add_gps(gps)
                ADRESA2GPS[self.vacc_centers[i].info['Adresa']] = gps
            else:
                no_data.append(i)
        for i in no_data:
            if self.vacc_centers[i].info['Adresa'] in ADRESA2GPS:
                self.vacc_centers[i].add_gps(ADRESA2GPS[self.vacc_centers[i].info['Adresa']])
        self.vacc_centers = [center for center in self.vacc_centers if len(center.gps) != 0]
        return None

    def _extract_links_from_soup(self, soup, region):
        centers_div = soup.select('div[class=center__container]')
        for center in centers_div:
            name = center.select_one('span[class=center__name]').text
            link = self.url + center.a['href']
            center_type = self._get_type_of_center(center.select_one('div[class="center__header_icons"]'))
            vacc_center = VaccCenter(name, region, link)
            vacc_center.add_center_type(center_type)
            self.vacc_centers.append(vacc_center)
        return None

    @staticmethod
    def _get_type_of_center(type_soup):
        center_type = copy.deepcopy(CENTER_TYPE)
        types = type_soup.find_all('span') + type_soup.find_all('img')
        types = set([typ['title'] for typ in types])
        if 'Bez registrace' in types:
            center_type['without_registration'] = 1
        if 'Příjem samoplátců' in types:
            center_type['self-payers'] = 1
        if 'Osoby starší 18 let' in types:
            center_type['18+'] = 1
        if 'Osoby ve věku 16-17 let' in types:
            center_type['16-17'] = 1
        if 'Očkování dětí 12+' in types:
            center_type['12-15'] = 1
        return center_type

    @staticmethod
    def _extract_info_from_soup(soup):
        table_info = soup.select('div[class=info] > table > tbody > tr')
        info = {i.select_one('td:nth-child(1)').text: i.select_one('td:nth-child(2)').text.replace("\r\n", "")
                for i in table_info[0:4]}
        info['Poznámka'] = table_info[4].select_one('td:nth-child(2)').text.replace("\t", " ").replace("\r\n", "")

        info['Vakcíny'] = [t.text for t in table_info[5].select_one('td:nth-child(2)').select('div[class=vaccineName]')]

        info['Dodatečné informace'] = [t.text.replace("👨\u200d🦽 ", "") for t in
                                       table_info[6].select_one('td:nth-child(2)').select('span')]

        info['Denní kapacita očkování'] = table_info[7].select_one('td:nth-child(2)').text.replace("\r\n", "")

        info['Způsob změny termínu druhé dávky vakcíny'] = [t.text.replace('\n', '') for t in
                                                            table_info[8].select_one('td:nth-child(2)' ).select('div')]
        return info

    @staticmethod
    def _extract_vaccines(info):
        vaccines = copy.deepcopy(VACCINES)
        for vac in info['Vakcíny']:
            vaccines[vac.split('/')[0]] = 1
        return vaccines

    @staticmethod
    def _extract_open_hours_from_soup(soup):
        open_table = soup.select('div[class=detail__aside] > div[class=opening] > table > tbody > tr')
        open_table = {i.select_one('td:nth-child(1)').text: i.select_one('td:nth-child(2)').text.strip().replace(" ", "")
                      for i in open_table}
        for day in open_table:
            hours = open_table[day].split("-")
            if hours[0] in ["Zavřeno", "Žádnádata"]:
                open_table[day] = [None, None]
            else:
                open_table[day] = [float(hours[0][:2]) + (float(hours[0][3:]) / 60),
                                   float(hours[1][:2]) + (float(hours[1][3:]) / 60)]
        return open_table


if __name__ == '__main__':
    v = VaccCentersScraper()
    v.get_links()
    v.get_information_about_centers()
    v.get_gps_of_centers()
    centers = v.vacc_centers
    centers[17].name
    centers[17].region
    centers[17].link
    centers[17].vacc_id
    centers[17].center_type
    centers[17].info
    centers[17].open_hours
    centers[17].vaccines
    centers[17].gps