import requests, threading, time, queue, urllib.request, \
    urllib.parse, urllib.error, http.cookiejar, colorama, json

from bs4 import BeautifulSoup
from colorama import Fore


colorama.init()
locker = threading.Lock()


def sprint(*a, **b):
    with locker:
        print(*a, **b)


class DB_proxies:
    def __init__(self, path):
        self.db = json.loads(open(path).read())
        self.path = path

    def add(self, data):
        proxy = data["ip:port"]
        type = data["type"]
        try:
            if self.db[proxy]:
                self.db[proxy]["score_active"] += 1
        except:
            score_active = 1
            _data = {proxy: {"type": type, "score_active": score_active}}
            self.db.update(_data)

    def get(self):
        return self.db

    def save(self):
        with open(self.path, "w") as f_db:
            json.dump(self.db, f_db)

    def print(self):
        for proxy in self.db:
            msg = Fore.BLUE + "[PROXY]\t" + Fore.WHITE + proxy + Fore.BLUE + "\t\t[АКТИВНОСТЬ]\t" + Fore.GREEN + str(self.db[proxy]["score_active"])
            print(msg)

    def to_list(self):
        my_list = []
        for proxy in self.db:
            my_list.append(proxy)
        return my_list


class ProxiesGrabber:

    def __init__(self, _log=False):
        self.proxies = {}

    def foxtools_parse(self):
        blue = Fore.BLUE
        white = Fore.WHITE
        urls = ['http://foxtools.ru/Proxy?page=1', 'http://foxtools.ru/Proxy?page=2', 'http://foxtools.ru/Proxy?page=3']
        for url in urls:
            if _log:
                sprint(Fore.BLUE + 'Парсинг: ' + Fore.WHITE + url)
            html = self.get_html(url)
            soup = BeautifulSoup(html, 'lxml')
            line = soup.find('table', id='theProxyList').find('tbody').find_all('tr')
            if _log:
                sprint(Fore.BLUE + 'Найдено ' + Fore.GREEN + str(len(line)) + Fore.BLUE + ' ip: ' + Fore.WHITE + url)
            for tr in line:
                td = tr.find_all('td')
                ip = td[1].text
                port = td[2].text
                country = td[3].text.replace('\xa0', '')
                anonym = td[4].text.replace('\r\n        ', '')
                types = td[5].text.replace('\r\n\t\t\t\t\t', '').replace('\r\n        ', '')
                time = td[6].text

                self.proxies[len(self.proxies)] = {'ip': ip,
                                                   'Порт': port,
                                                   'Страна': country,
                                                   'Анонимность': anonym,
                                                   'Тип': types,
                                                   'Время отклика': time}

    def free_proxy_list_parse(self):
        url = "https://free-proxy-list.net/"
        if _log:
            sprint(Fore.BLUE + 'Парсинг: ' + Fore.WHITE + url)
        html = self.get_html(url)
        soup = BeautifulSoup(html, 'lxml')
        list_proxies = soup.findAll(class_='form-control')[0].getText().splitlines()
        del list_proxies[0:3]
        if _log:
            sprint(
                Fore.BLUE + 'Найдено ' + Fore.GREEN + str(len(list_proxies)) + Fore.BLUE + ' ip: ' + Fore.WHITE + url)
        for el in list_proxies:
            # print(el)
            list_el = el.split(':')
            ip = list_el[0]
            port = list_el[1]
            country = ''
            anon = ''
            types = ''
            ping = ''
            self.proxies[len(self.proxies)] = {'ip': ip,
                                               'Порт': port,
                                               'Страна': country,
                                               'Анонимность': anon,
                                               'Тип': types,
                                               'Время отклика': ping}

    def get_proxies(self):
        t1 = threading.Thread(target=self.foxtools_parse)
        t1.setDaemon(True)
        t1.start()
        t2 = threading.Thread(target=self.free_proxy_list_parse)
        t2.setDaemon(True)
        t2.start()

        t1.join()
        t2.join()
        # self.foxtools_parse()
        # self.free_proxy_list_parse()
        list_proxies = []
        for i in range(len(self.proxies)):
            list_proxies.append(self.proxies[i]['ip'] + ':' + self.proxies[i]['Порт'])
        return list_proxies

    def get_html(self, url):
        try:
            r = requests.get(url)
            return r.text
        except requests.exceptions.ConnectionError as errc:
            if _log:
                sprint(Fore.RED + 'Ошибка соединения: ' + Fore.WHITE + url)


class ProxiesChecker:
    def __init__(self, list_proxies):
        self.test_url = 'http://www.google.com/humans.txt'
        #self.test_url = 'https://www.instagram.com'
        self.timeout_value = 10
        self.max_thread = 100
        self.list_proxies = list_proxies
        self.workers = []
        self.good_proxies = []
        self.db = DB_proxies("db_proxies.json")

    def CheckingProcessThread(self, _id, q):
        while True:
            proxy = q.get()
            log_msg = str(Fore.BLUE + "Поток #" + Fore.GREEN + "%3d" % (
                _id) + Fore.BLUE + ".  Проверка прокси (HTTPS)" + Fore.WHITE + "%21s \t\t" % (proxy))

            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({'https': 'https://' + proxy}),
                urllib.request.HTTPHandler(),
                urllib.request.HTTPSHandler()
            )

            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)

            try:
                t1 = time.time()
                response = urllib.request.Request('https://www.instagram.com/')
                urllib.request.urlopen(response, timeout=self.timeout_value)
                t2 = time.time()
            except Exception as e:
                log_msg += Fore.RED + "%s (%s)" % ("ПЛОХОЙ ", str(e))
                sprint(log_msg)
                q.task_done()
                continue
            log_msg += Fore.GREEN + "ХОРОШИЙ " + Fore.BLUE + " Время отклика: " + Fore.GREEN + "%d" % int(
                (t2 - t1) * 1000) + Fore.BLUE + ", длина ответа=" + Fore.GREEN + "%s" % ("1")
            sprint(log_msg)
            proxy_data = {"ip:port" : proxy,
                          "type" : "https",
                          "score_active" : 0}
            self.db.add(proxy_data)
            self.good_proxies.append(proxy)
            q.task_done()

    def run(self):
        input_queue = queue.Queue()
        for proxy in self.list_proxies:
            input_queue.put(proxy)

        for i in range(self.max_thread):
            t = threading.Thread(target=self.CheckingProcessThread, args=(i, input_queue,))
            t.setDaemon(True)
            t.start()
            self.workers.append(t)

        input_queue.join()
        self.db.save()
        return self.good_proxies


def export(list_proxies, port="all", country="all", anonym="all", types="all", time="all"):
    if _log:
        print('Экспорт прокси в файл: proxyes.txt')
    with open('proxyes.txt', 'w') as f:
        for i in range(len(list_proxies)):
            # if port != "all":
            #    if port != self.proxies[i]['Порт']:
            #        continue
            # if country != "all":
            #    if country != self.proxies[i]['Страна']:
            #        continue
            # if anonym != "all":
            #    if anonym != self.proxies[i]['Анонимность']:
            #        continue
            # if types != "all":
            #    if types != self.proxies[i]['Тип']:
            #        continue
            # if time != "all":
            #    if time < int(self.proxies[i]['Страна']):
            #        continue
            f.write(list_proxies[i] + '\n')
    if _log:
        print('Экспорт окончен')


if __name__ == '__main__':
    _log = True
    i = "3"
    if i == "1":
        grabb = ProxiesGrabber(_log)
        all_proxies = grabb.get_proxies()
        check = ProxiesChecker(all_proxies)
        good_proxies = check.run()
        export(good_proxies)
    elif i == "2":
        db = DB_proxies("db_proxies.json")
        db.print()
    elif i == "3":
        db = DB_proxies("db_proxies.json")
        _list = db.to_list()
        export(_list)
    elif i == "4":
        p = open("http.txt")


