import json
import socket
import gzip
import StringIO
import base64
import sys
import time
import datetime
import threading

import requests
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA512
import urllib

def convert_ticks_to_datetime(s):
    return datetime.datetime(1, 1, 1) + datetime.timedelta(microseconds=int(s)/10)


class FairlayPythonClient(object):

    MARKET_CATEGORY = {
        1: 'Soccer',
        2: 'Tenis',
        3: 'Golf',
        4: 'Cricket',
        5: 'RugbyUnion',
        6: 'Boxing',
        7: 'Horse Racing',
        8: 'Motorsport',
        10: 'Special',
        11: 'Rugby League',
        12: 'Bascketball',
        13: 'American Football',
        14: 'Baseball',
        15: 'Politics',
        16: 'Financial',
        17: 'Greyhound',
        18: 'Volleyball',
        19: 'Handball',
        20: 'Darts',
        21: 'Bandy',
        22: 'Winter Sports',
        24: 'Bowls',
        25: 'Pool',
        26: 'Snooker',
        27: 'Table tennis',
        28: 'Chess',
        30: 'Hockey',
        31: 'Fun',
        32: 'eSports',
        33: 'Inplay',
        34: 'reserved4',
        35: 'Mixed Martial Arts',
        36: 'reserved6',
        37: 'reserved',
        38: 'Cycling',
        39: 'reserved9',
        40: 'Bitcoin',
        42: 'Badminton'
    }

    MARKET_TYPE = {
        0: 'MONEYLINE',
        1: 'OVER_UNDER',
        2: 'OUTRIGHT',
        3: 'GAMESPREAD',
        4: 'SETSPREAD',
        5: 'CORRECT_SCORE',
        6: 'FUTURE',
        7: 'BASICPREDICTION',
        8: 'RESERVED2',
        9: 'RESERVED3',
        10: 'RESERVED4',
        11: 'RESERVED5',
        12: 'RESERVED6'

    }

    MARKET_PERIOD = {
        0: 'UNDEFINED',
        1: 'FT',
        2: 'FIRST_SET',
        3: 'SECOND_SET',
        4: 'THIRD_SET',
        5: 'FOURTH_SET',
        6: 'FIFTH_SET',
        7: 'FIRST_HALF',
        8: 'SECOND_HALF',
        9: 'FIRST_QUARTER',
        10: 'SECOND_QUARTER',
        11: 'THIRD_QUARTER',
        12: 'FOURTH_QUARTER',
        13: 'FIRST_PERIOD',
        14: 'SECOND_PERIOD',
        15: 'THIRD_PERIOD',
    }

    MARKET_SETTLEMENT = {
        0: 'BINARY',
        1: 'DECIMAL'
    }

    MATCHED_ORDER_STATE = {
        0: 'MATCHED',
        1: 'RUNNER_WON',
        2: 'RUNNER_HALFWON',
        3: 'RUNNER_LOST',
        4: 'RUNNER_HALFLOST',
        5: 'MAKERVOIDED',
        6: 'VOIDED',
        7: 'PENDING',
        8: 'DECIMAL_RESULT'
    }

    UNMATCHED_ORDER_STATE = {
        0: 'ACTIVE',
        1: 'CANCELLED',
        2: 'MATCHED',
        3: 'MATCHEDANDCANCELLED'
    }

    ORDER_TYPE = {
        0: 'MAKERTAKER',
        1: 'MAKER',
        2: 'TAKER'
    }

    ENDPOINTS = {
        'get_orderbook': 1,
        'get_server_time': 2,
        'get_market': 6,
        'create_market': 11,
        'cancel_all_orders': 16,
        'get_balance': 22,
        'get_unmatched_orders': 25,
        'get_matched_orders': 27,
        'set_absence_cancel_policy': 43,
        'set_force_nonce': 44,
        'set_read_only': 49,
        'change_orders': 61,
        'cancel_orders_on_markets': 83,
        'change_closing': 84,
        'settle_market': 86
    }

    CONFIG = {
        'SERVERIP': '31.172.83.53',
        'PORT': 18017,
        'APIAccountID': 1,
        'ID': 'CHANGETHIS',
        'SERVERPUBLICKEY': ('-----BEGIN PUBLIC KEY-----\n'
                            'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC52cTT4XaVIUsmzfDJBP/ZbneO\n'
                            '6qHWFb01oTBYx95+RXwUdQlOAlAg0Gu+Nr8iLqLVbam0GE2OKfrcrSy0mYUCt2Lv\n'
                            'hNMvQqhOUGlnfHSvhJBkZf5mivI7k0VrhQHs1ti8onFkeeOcUmI22d/Tys6aB20N\n'
                            'u6QedpWbubTrtX53KQIDAQAB\n'
                            '-----END PUBLIC KEY-----')
    }

    def __init__(self):
        super(FairlayPythonClient, self).__init__()
        self.__load_config()
        self.__last_time_check = None
        self.__offset = None

    def __load_config(self):
        try:
            with open('config.txt') as config:
                try:
                    temp = json.load(config)
                    self.CONFIG.update(temp)

                    if 'ID' not in self.CONFIG.keys() or self.CONFIG['ID'] in ['', 'CHANGETHIS']:
                        raise EnvironmentError('Missing user ID in config file')

                    required_keys = ['PrivateRSAKey', 'PublicRSAKey']
                    if [x for x in required_keys if x not in self.CONFIG.keys() or not self.CONFIG[x]]:
                        raise EnvironmentError('Missing user ID or Public/Private keys in config file')
                except ValueError:
                    raise EnvironmentError('Something is wrong with the config file')
        except IOError:
            self.__generate_keys()

            with open('config.txt', 'w') as config:
                json.dump(self.CONFIG, config, indent=4)

            print '==================================================================='
            print 'It appears that you don\'t have a config file, so we created'
            print 'a new one with a brand new key pair.'
            print ''
            print 'Please visit:  http://fairlay.com/user/dev and register a new API'
            print 'Account with the following public key:'
            print ''
            print self.CONFIG['PublicRSAKey']
            print ''
            print '** Don\'t forget to to change ID and APIAccountID fields in'
            print '   the config.txt file.'
            print '==================================================================='
            print ''
            sys.exit(0)

    def __generate_keys(self, bits=2048):
        new_key = RSA.generate(bits, e=65537)
        public_key = new_key.publickey().exportKey('PEM')
        private_key = new_key.exportKey('PEM')
        self.CONFIG['PublicRSAKey'] = public_key
        self.CONFIG['PrivateRSAKey'] = private_key

    def __send_request(self, endpoint, data=None):
        nonce = int(round(time.time() * 1000))
        endpoint_code = self.ENDPOINTS[endpoint] + 1000 * self.CONFIG['APIAccountID']

        message = "{}|{}|{}".format(nonce, self.CONFIG['ID'], endpoint_code)
        if data:
            message += '|' + data
        sign = self.__sign_message(message)
        message = '{}|{}<ENDOFDATA>'.format(sign, message)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15)
            s.connect((self.CONFIG['SERVERIP'], self.CONFIG['PORT']))
            s.send(message)

            data = ''
            while True:
                new_data = s.recv(4096)
                if not new_data:
                    break
                data += new_data
            s.close()
            response = gzip.GzipFile(fileobj=StringIO.StringIO(data)).read()
        except socket.timeout, socket.error:
            return

        if not self.__verify_response(response):
            raise ValueError

        response = response.split('|')[-1]

        if response == 'XError: Service unavailable':
            time.sleep(6)
            return self.__send_request(endpoint, data)

        if response.startswith('XError'):
            raise IOError(response.replace('XError:', ''))
        return response

    def __verify_response(self, message):
        idx = message.find('|')
        if idx == -1:
            return True

        signed_message = message[:idx]
        original_message = message[idx+1:]
        key = RSA.importKey(self.CONFIG['SERVERPUBLICKEY'])
        signer = PKCS1_v1_5.new(key)
        digest = SHA512.new()
        digest.update(original_message)
        if signer.verify(digest, base64.b64decode(signed_message + "=" * ((4 - len(signed_message) % 4) % 4))):
            return True

    def __sign_message(self, message):
        key = RSA.importKey(self.CONFIG['PrivateRSAKey'])
        signer = PKCS1_v1_5.new(key)
        digest = SHA512.new()
        digest.update(message)
        sign = signer.sign(digest)
        return base64.b64encode(sign)

    def __public_request(self, endpoint, json=True, tries=0):

        try:
            response = requests.get('http://31.172.83.181:8080/free/' + endpoint)

            if response == 'XError: Service unavailable':
                raise requests.exceptions.ConnectionError

            if 'XError' in response.text:
                return

            if json:
                return response.json()
            else:
                return response
        except requests.exceptions.ConnectionError:
            time.sleep(6)
            if tries >= 3:
                raise requests.exceptions.ConnectionError
            return self.__public_request(endpoint, json, tries + 1)

    def get_markets_and_odds(self, market_filter={}, changed_after=datetime.datetime(2015, 1, 1)):
        '''
            Free Public API for retrieving markets and odds. Check the documentation at:
            http://piratepad.net/APVEoUmQPS

            market_filter: dictionary
            change_after: datetime

        Response: dictionary
            E.g. {'Ru': [{'RedA': 0.0, 'VisDelay': 3000, 'Name': 'Yes', 'VolMatched': 0.0},
                         {'RedA': 0.0, 'VisDelay': 3000, 'Name': 'No', 'VolMatched': 0.0}],
                  'LastSoftCh': '2015-11-30T00:50:09.2443208Z', 'Descr': 'This market resolves to ...',
                  'Title': 'Will OKCoin lose customer funds in 2016?', 'OrdBStr': '~', 'MarketCategory': 'Bitcoin',
                  'Status': 0, '_Type': 2, 'CatID': 40, 'LastCh': '2015-10-30T06:05:00.7541435Z',
                  'Comp': 'Bad News', 'MarketType': 'MONEYLINE', 'OrdBJSON': [], 'Comm': 0.02,
                  'ClosD': '2016-10-01T00:00:00', 'Margin': 10000.0, 'ID': 57650700754, 'MaxVal': 0.0,
                  'SettlT': 0, 'MinVal': 0.0, 'CreatorName': 'FairMM', 'Pop': 0.0, 'MarketPeriod': 'FIRST_SET',
                  'SettlD': '2017-01-01T00:00:00', '_Period': 1, 'SettlementType': 'BINARY'}
        '''

        if not self.__last_time_check or self.__last_time_check + datetime.timedelta(minutes=10) < datetime.datetime.now():
            try:
                response = self.__public_request('time')
                if not response:
                    raise ValueError
            except Exception:
                return []

            self.__offset = datetime.datetime.now() - convert_ticks_to_datetime(response)
            self.__last_time_check = datetime.datetime.now()

        changed = changed_after - datetime.timedelta(seconds=10) - self.__offset
        filters = {'ToID': 10000, 'SoftChangedAfter': changed.isoformat()}
        filters.update(market_filter)

        try:
            response = self.__public_request('markets/{}'.format(json.dumps(filters)))
        except ValueError:
            return []

        for market in response:
            self.__parse_market(market)
        return response

    def __parse_market(self, market):
        market['MarketCategory'] = self.MARKET_CATEGORY[market['CatID']]
        market['MarketType'] = self.MARKET_TYPE[market['_Type']]
        market['MarketPeriod'] = self.MARKET_PERIOD[market['_Period']]
        market['SettlementType'] = self.MARKET_SETTLEMENT[market['SettlT']]
        if market['OrdBStr']:
            market['OrdBJSON'] = [json.loads(ob) for ob in market['OrdBStr'].split('~') if ob]

    def get_server_time(self):
        '''
        Response: string
            E.g. '636093693129714057'
        '''
        return self.__send_request('get_server_time')

    def get_balance(self):
        '''
        Response: dictionary
            E.g. {'RemainingRequests': 9893, 'PrivReservedFunds': 180.9493999999995,
                  'AvailableFunds': 42.4242, 'CreatorUsed': 0.0,
                  'SettleUsed': 0.0, 'MaxFunds': 0.0, 'PrivUsedFunds': 25.0}
        '''
        response = self.__send_request('get_balance')
        if response:
            try:
                return json.loads(response)
            except ValueError:
                return None

    def get_orders(self, order_type, timestamp=1420070400L, market_id=None):
        '''
            When two open orders are matched, a Matched Order is created in the PENDING state.
            If the maker of the bet cancels his bet within a certain time period (usually 0, 3 or 6 seconds depending on the market)
                the bet goes into the state MAKERVOIDED and is void.
            When a market is settled the orders to in one of the settled states VOID, WON, HALFWON, LOST or HALFLOST.
            Decimal market go into the state DECIMALRESULT while the settlement value DecResult will be set.

        Request:
            order_type: 'matched' or 'unmatched'

        Response: list of dictionaries

            E.g. (matched orders)
                [{'_UserUMOrderID': 636089384190025705,
                  '_UserOrder': {'RunnerID': 2, 'OrderID': 636089384190025711, 'MatchedSubUser':
                                   'fairlay_user', 'BidOrAsk': 1, 'MarketID': 84402058841},
                  '_MatchedOrder': {'State': 3, 'Price': 11.534, 'Amount': 8.0, 'MakerCancelTime': 0,
                                      'DecResult': 0.0, 'R': 0, 'ID': 636089384190025711, 'Red': 0.0},
                  'StatusStr': 'RUNNER_LOST'
                }]

                (unmatched orders)
                [{'_UnmatchedOrder': {
                    '_Type': 0, 'Price': 1.25, 'PrivCancelAt': 3155378975999999999, 'PrivSubUser': 'fairlay-1',
                    'State': 0, 'PrivAmount': 20.0, 'makerCT': 0, 'RemAmount': 20.0, 'PrivUserID': 1100080,
                    'PrivID': 636116964109686557, 'BidOrAsk': 0
                 },
                 '_UserOrder': {
                    'RunnerID': 0, 'OrderID': 636116964109686557, 'MatchedSubUser': None, 'BidOrAsk': 0,
                    'MarketID': 85924869998
                 },
                 'StatusStr': 'ACTIVE', TypeStr = 'MAKERTAKER'
                }]
        '''
        max_items = 1500
        start = 0
        orders = []

        while True:
            if market_id:
                message = str(timestamp) + '|' + str(market_id)
            else:
                message = str(timestamp) + '|' + str(start) + '|' + str(start + max_items)

            response = self.__send_request('get_'+ order_type +'_orders', message)

            try:
                temp = json.loads(response)
                if market_id:
                    return temp
                orders += temp
            except ValueError:
                break

            if len(temp) < max_items:
                break
            else:
                start += max_items

        for o in orders:
            status = o['_MatchedOrder'] if order_type == 'matched' else o['_UnmatchedOrder']
            o['StatusStr'] = self.MATCHED_ORDER_STATE[status['State']]
            if order_type == 'unmatched':
                o['TypeStr'] = self.ORDER_TYPE[status['_Type']]
        return orders

    def change_orders(self, orders_list=[]):
        '''
        Request:
            Allows you to create, cancel and alter orders
            Set Pri to 0  to cancel an order
            Set Oid to -1 to create an order
            ** Maximum allowed orders in one request: 50

            orders_list:
                Mid: Market ID
                Rid: Runner ID  I.E.: 0 -> 1st runner, 1 -> 2nd runner, ...
                Oid: Order ID  (should be set to -1 if no old order shall be replaced)
                Am: Amount in mBTC. In case of ask orders this amount represents the liability, in case of bid orders this amount represents the possible winnings.
                Pri: Price with 3 decimals
                Sub:  Custom String
                Type: 0 -> MAKERTAKER, 1 -> MAKER, 2 -> TAKER
                Boa: Must be 0 for Bid Orders  and 1 for Ask.  Ask means that you bet on the outcome to happen.
                Mct: Should be set to 0

        Response: list of dictionaries
            E.g. [{'_Type': 0, 'Price': 5.33, 'PrivCancelAt': 3155378975999999999,
                   'PrivSubUser': '', 'State': 0, 'PrivAmount': 5.0, 'makerCT': 0, 'RemAmount': 5.0,
                   'PrivUserID': 1100080, 'PrivID': 636093725357177200, 'BidOrAsk': 1}]
        '''
        if len(orders_list) > 50:
            return

        message = []
        for order in orders_list:
            temp = {}
            for k, v in order.items():
                temp[k] = str(v) if k in ['Mid', 'Rid', 'Oid'] else v
            message.append(temp)
	print message
        response = self.__send_request('change_orders', json.dumps(message))

        try:
            response = json.loads(response)
	    print response
        except ValueError:
            return None

        markets_to_cancel = []
        response_orders = []
        for idx, order in enumerate(orders_list):
            response_order = response[idx]
            if 'YError:Market Closed' in response_order or response_order == 'Order cancelled':
                pass
            elif 'YError' in response_order:
                markets_to_cancel.append(orders_list[idx]['Mid'])
                response[idx] = '{"error": "' + response[idx].split(':')[1] + '"}'
        self.cancel_orders_on_markets(markets_to_cancel)
        return [json.loads(x) for x in response]

    def get_market(self, market_id):
        '''
        Request:
            market_id: string or int

        Response:
            dictionary (see example in get_markets_and_odds above)
        '''
        message = str(market_id)
        response = self.__send_request('get_market', message)

        try:
            market = json.loads(response)
            self.__parse_market(market)
            return market
        except ValueError:
            return None

    def get_odds(self, market_id):
        '''
        Request:
            market_id: string or int

        Response: dictionary
            E.g. [{'S': 1, 'Bids': [[2.573, 19.0]], 'Asks': [[3.752, 13.0]]}]
        '''
        message = str(market_id)
        response = self.__send_request('get_orderbook', message)

        if not ('Bids' in response or 'Asks' in response):
            return []
        try:
            return [json.loads(ob) for ob in response.split('~') if ob]
        except ValueError:
            return []

    def create_market(self, data):
        '''
        Request:
            data: dictionary
                competition: string
                description: string
                title: string,
                category: must be an ID from CATEGORIES
                closing_date: string in format YYYY-MM-DDTHH:MM:SS
                resolution_date: string in format YYYY-MM-DDTHH:MM:SS
                username: string
                outcomes: list of strings ie: ['Outcome X', 'Outcome Y']
        '''

        if data['category'] not in self.CATEGORIES.values():
            return

        dic = {
            'Comp': data['competition'],
            'Descr': data['description'],
            'Title': data['title'],
            'CatID': data['category'],
            'ClosD': data['closing_date'],
            'SettlD': data['resolution_date'],
            'PrivCreator': self.CONFIG['ID'],
            'CreatorName': data['username'],
            'Status': 0,
            '_Type': 2,
            '_Period': 1,
            'SettlT': 0,
            'Comm': 0.02,
            'Pop': 0.0,
            'Ru': []
        }

        for run in data['outcomes']:
            dic['Ru'].append({'Name': run, 'InvDelay': 0, 'VisDelay': 0})

        message = json.dumps(dic)
        return self.__send_request('create_market', message)

    def cancel_orders_on_markets(self, market_ids=[]):
        '''
        Response: int (number of cancelled orders)
        '''
        response = self.__send_request('cancel_orders_on_markets', str([str(x) for x in market_ids]))
        return int(response.split(' ')[0])

    def cancel_all_orders(self):
        '''
        Response: int (number of cancelled orders)
        '''
        response = self.__send_request('cancel_all_orders')
        if response:
            return int(response.split(' ')[0])

    def change_closing(self,market_id,closing_date,resolution_date):
        '''
        Request:
            market_id: Market ID
            closing_date: Market closing date, string in format YYYY-MM-DDTHH:MM:SS
            resolution_date: Market resolution date string in format YYYY-MM-DDTHH:MM:SS
                (Settlement date should be bigger than Closing date)

        Return: "Market time changed"  or some kind of "XError: ..."
        '''

        dic = {
            'MID':market_id,
            'ClosD':closing_date,
            'SetlD':resolution_date
        }

        message = json.dumps(dic)
        return self.__send_request('change_closing', message)

    def settle_market(self,data):
        '''
        Request:
            data: dictionary
                Mid:  is the market ID
                Runner:  determines the Runner which won (0 means that the 1st Runner won, 1 means that the 2nd Runner won and so on). If a market shall be voided the Runner must be set to -1
                Win:  Must be set to 1
                Half:  should be set to "false". Only needed for  +- 0.25  and +-0.75  soccer  spread and over/under markets. If a market is half won or half lost, set Half to "true";
                Dec:   If the market is not binary, but has a decimal outcome, this needs to be set to the result.  [Not supported yet]
                ORed:   Odds reduction  [only for Horse racing - not needed in general]

            example:
            data = {
                'Mid' : '9101010101',
                'Runner' :0,
                'Win' : 1,
                'Half' : False,
                'Dec' : 0.0,
                'ORed' : 0.0
            }

        Return  "Market settled" or some kind of "XError: ..."
        '''

        message = json.dumps(data)
        return self.__send_request('settle_market', message)

    def set_absence_cancel_policy(self, miliseconds):
        '''
        Request:
            miliseconds: float or string

        Response: bool
        '''
        response = self.__send_request('set_absence_cancel_policy', str(miliseconds))
        return True if response =='success' else False

    def set_force_nonce(self, force):
        '''
        Request:
            force: bool

        Response: bool
        '''
        force = 'true' if force else 'false'
        response = self.__send_request('set_force_nonce', force)
        return True if response =='success' else False

    def set_ready_only(self):
        '''
        Response: bool
        '''
        response = self.__send_request('set_ready_only')
        if 'success' in response:
            return True

# client = FairlayPythonClient()
# print client.get_orders('unmatched')
# print '--------'
# print client.get_orders('matched')


###############################################################################
###############################################################################

class FairlayMarketFetcher(object):
    markets = []
    last_fetch_date = datetime.datetime(2016, 1, 1)

    def __init__(self):
        super(FairlayMarketFetcher, self).__init__()
        self.client = FairlayPythonClient()
        self.event = threading.Event()
        threading.Thread(target=self.__run).start()

    def __run(self):
        while not self.event.is_set():
            self.fetch_new_markets()
            self.last_fetch_date = datetime.datetime.now()
            self.event.wait(60 * 5)  # 5 minutes

    def fetch_new_markets(self):
        from_id = 0
        increment = 100

        new_markets = []
        while True:
            filters = {'FromID': from_id, 'ToID': from_id + increment}
            new_markets += self.client.get_markets_and_odds(filters, self.last_fetch_date)

            if len(new_markets) < increment:
                break
            else:
                from_id += increment
            time.sleep(2)

        now = datetime.datetime.now() - datetime.timedelta(minutes=30)
        for idx, market in enumerate(self.markets):
            closing_date = datetime.datetime.strptime(market['ClosD'][:19], '%Y-%m-%dT%H:%M:%S')
            if closing_date < now:
                del self.market[idx]

        self.markets += new_markets

    def stop(self):
        self.event.set()

# fetcher = FairlayMarketFetcher()
# while True:
#     try:
#         time.sleep(1)
#     except KeyboardInterrupt:
#         fetcher.stop()
#         break



###############################################################################
###############################################################################

class FairlayOrderMatching(object):
    matched_orders = []
    created_order = {'id': None, 'market': None, 'odds': None}
    
    def create_order(self, idd, market, price, am, boa):
        if not self.created_order['market']:
            order = {
                'Mid': market,
                'Rid': 0,
                'Oid': idd,
                'Am': am * 1000,
                'Pri': price,
                'Sub': '',
                'Type': 0,
                'Boa': boa,
                'Mct': 0
            }
	    print price
            order = self.client.change_orders([order])[0]
            if order:
		order = order
                return order
    
    def __init__(self):
        super(FairlayOrderMatching, self).__init__()
        self.client = FairlayPythonClient()
	       
	matched = self.client.get_orders('matched')

	
	self.tralala = self.dothis()
    def create_wait_get_matched(self):
        order = {
            'Mid': 82339763895,
            'Rid': 0,
            'Oid': -1,
            'Am': 5,
            'Pri': 5.645,
            'Sub': '',
            'Type': 0,
            'Boa': 1,
            'Mct': 0
        }
        order = self.client.change_orders([order])[0]

        if order:
            order_id = order['PrivID']

            time.sleep(6)
            temp = self.client.get_orders('matched')

            for match in temp:
                if match['_UserUMOrderID'] == order_id:
                    self.matched_orders.append(match)

        return self.matched_orders

    def calculate_position(self, market_id):
        '''
            Calculate user position for each runner in the specified market ID
            Return possible winnings and losing for each runner in BTC
        '''
        position = {}
        matched = self.client.get_orders('matched')

        for order in matched:
            m_id = order['_UserOrder']['MarketID']
            r_id = order['_UserOrder']['RunnerID']
            is_back = order['_UserOrder']['BidOrAsk'] == 1
            amount = order['_MatchedOrder']['Amount'] / 1000.0
            odds = order['_MatchedOrder']['Price']

            if m_id != market_id:
                continue

            winnings = losings = 0
            if is_back:
                winnings += (amount * odds) - amount
                losings += -amount
            else:
                winnings += -amount
                losings += (amount * (1 + (1 / (odds - 1)))) - amount

            if r_id in position.keys():
                position[r_id]['possible_winnings'] += winnings
                position[r_id]['possible_losings'] += losings
            else:
                position[r_id] = {
                    'possible_winnings': winnings,
                    'possible_losings': losings
                }

        total_losings = sum([m['possible_losings'] for m in position.values()])
        for key, d in position.items():
            position[key]['possible_losings'] += total_losings - d['possible_losings']

        return position
    def dothis(self):

	while 1:	
		print 'i'
		sessionBetBTC = requests.Session()
		sessionBetBTC.headers.update({'Authorization': 'Token token=CHANGEME'})
		'''
		r9= sessionBetBTC.delete('https://www.betbtc.co/api/bet/3?selection=all')
		print r9.text 
		'''
		##betbtc unmatched orders
		u1 = sessionBetBTC.get('https://www.betbtc.co/api/bet/?id=unmatched')
		print json.loads(u1.text)
	
		##[[

#  BET_ID,
#"EVENT_NAME",
#MARKET_ID,
#"SELECTION_NAME",
#"ODD",
#"STAKE",
#"BET_TYPE"

#]]
		for bet in json.loads(u1.text):
		
			u2 = sessionBetBTC.get('https://www.betbtc.co/api/market/?id=' + str(bet[2]))
			for winner in json.loads(u2.text):
				if bet[3] in winner:
					back = winner[bet[3]]['Back'][0][0]
					lay = winner[bet[3]]['Lay'][0][0]
					if 'lay' in bet[6]:
						
						if type(lay) is float:
							u3 = sessionBetBTC.put('https://www.betbtc.co/api/bet/' + str(bet[0]) + '?odd=' + str(lay))
							print json.loads(u3.text)
						else:
							print 'lay is not float'
					elif 'back' in bet[6]:
						if type(back) is float:
							u3 = sessionBetBTC.put('https://www.betbtc.co/api/bet/' + str(bet[0]) + '?odd=' + str(back))
							print json.loads(u3.text)
						else:
							print 'back is not float'
						
					
		#Fairlay unmatched		
		unmatched = self.client.get_orders('unmatched')

		for order in unmatched:
			print order
			marketId = order['_UserOrder']['MarketID']
			BidOrAsk = order['_UserOrder']['BidOrAsk']
			OrderID = order['_UserOrder']['OrderID']
			sessionFairlay = requests.Session()
			r4 = sessionFairlay.get('http://31.172.83.181:8080/free/markets/{"Cat":2,"OnlyActive":true,"ToID":10000}')
			for contest in json.loads(r4.text):
				if marketId is contest['ID']: #angel bid and lay, ask and back
					
					FairlayBid = json.loads(contest['OrdBStr'][:-1])['Bids'][0][0]
					FairlayAsk = json.loads(contest['OrdBStr'][:-1])['Asks'][0][0]
					FairlayBid = 1 / (1 - (1 / FairlayBid))
					FairlayAsk = 1 / (1 - (1 / FairlayAsk))									
					if BidOrAsk == 0:					
						order = {
						'Mid': marketId,
						'Rid': 0,
						'Oid': OrderID,
						'Am': _UnmatchedOrder['RemAmount'],
						'Pri': FairlayAsk,
						'Sub': '',
						'Type': 0,
						'Boa': BidOrAsk,
						'Mct': 0
					    }
					elif BidOrAsk == 1:
						order = {
						'Mid': marketId,
						'Rid': 0,
						'Oid': OrderID,
						'Am': _UnmatchedOrder['RemAmount'],
						'Pri': FairlayBid,
						'Sub': '',
						'Type': 0,
						'Boa': BidOrAsk,
						'Mct': 0
					    }
				        order = self.client.change_orders([order])[0]
				        if order:
					    order = order
					    print order
					 	
						
		#time.sleep(60)
		r1 = sessionBetBTC.get('https://www.betbtc.co/api/user/statement')
		print r1.text
		betBTCBal = json.loads(r1.text)[0]['balance']
		FairlayBal = self.client.get_balance()['AvailableFunds'] / 1000
		print betBTCBal
		print FairlayBal
		if betBTCBal < FairlayBal:
			lowBal = betBTCBal / 1
		elif betBTCBal >= FairlayBal:
			lowBal = FairlayBal / 1
		lowBal = 0.0025
		#lowBal = 0.0049 / 6
		#tennis
		#matchodds / Set 1
		#betBTC
		r2 = sessionBetBTC.get('https://www.betbtc.co/api/event?sport=3')
		for contest in json.loads(r2.text):
			try:
				theContest = contest
				theId = contest[0]
				#print theId
				found = False
				with open('ids.txt', 'r') as ids:
					for x in ids:
						x = x.rstrip()
				#		print x
						if str(theId) in x:
							found = True
							print 'found!'
				if not found: 
					theName = contest[1]
					if contest[7] == 'Set 1 Winner':
						r3 = sessionBetBTC.get('https://www.betbtc.co/api/market/?id=' + str(contest[0]))
						if 'status' not in json.loads(r3.text)[0]:
							name = contest[6][0]['name']
							name2 = contest[6][1]['name']
			
							#Fairlay
							sessionFairlay = requests.Session()
							r4 = sessionFairlay.get('http://31.172.83.181:8080/free/markets/{"Cat":2,"OnlyActive":true,"ToID":10000}')
							for contest in json.loads(r4.text):
								if name in contest['Ru'][0]['Name']: #angel bid and lay, ask and back
									if contest['_Type'] == 0 and contest['_Period'] == 2:
						
						
										FairlayBid = json.loads(contest['OrdBStr'][:-1])['Bids'][0][0]
										FairlayAsk = json.loads(contest['OrdBStr'][:-1])['Asks'][0][0]
										FairlayBidVol = json.loads(contest['OrdBStr'][:-1])['Bids'][0][1] / 1000
										FairlayAskVol = json.loads(contest['OrdBStr'][:-1])['Asks'][0][1] / 1000
										FairlayBid2 = 1 / (1 - (1 / FairlayBid))
										FairlayAsk2 = 1 / (1 - (1 / FairlayAsk))									
										print FairlayBid
										print FairlayAsk
										print FairlayBid2
										print FairlayAsk2
										betbtc= json.loads(r3.text)	
										for winner in betbtc:
											if name in winner:
												back = winner[name]['Back'][0][0]
												backVol = winner[name]['Back'][0][1]
												lay = winner[name]['Lay'][0][0]
												layVol = winner[name]['Lay'][0][1]
											
												if type(back) is float and type(lay) is float:
													back2 = 1 / (1 - (1 / back))
													lay2 = 1 / (1 - (1 / lay))
													w1 = (1 / float(FairlayBid)) + (1 / float(lay2))
													w2 = (1 / float(FairlayAsk2)) + (1 / float(back))
													if w1 < .9 and w1 > .6:
														if w2 < w1:
															print FairlayAskVol		
															print backVol
															print 1
															print theName
															print contest['Title']
															print w2
															#2 = 32 / ( 16 * 2 )
															#16 = 32 / ( 2 * 2)
															#w2 = 1 / ( bet1 * FairlayAsk)
															#w2 = 1 / ( 2.41 * 2.78)
															#w2 = 0.149258187
															bet1 = 1 / (w2 * FairlayAsk2)
														
															bet2 = 1 / (w2 * back)
															bVol = backVol	
															aVol = FairlayAskVol
															print FairlayAsk2
															print back
															idealbet1 = (aVol + bVol) * bet1
															idealbet2 = (aVol + bVol) * bet2
															if idealbet1 > aVol:
																idealbet2 = (aVol / bet1) * bet2
																idealbet1 = aVol
															elif idealbet2 > bVol:
																idealbet1 = (bVol / bet2) * bet1
																idealbet2 = bVol
															print 'aVol: ' + str(aVol)
															print 'bVol: ' + str(bVol)
															print 'idealbet1: ' + str(idealbet1)
															print 'idealbet2: ' + str(idealbet2)
															if lowBal < idealbet1 or lowBal < idealbet2:
																idealbet1 = bet1 * lowBal
																idealbet2 = bet2 * lowBal
																bet1 = idealbet1
																bet2 = idealbet2
															else:
																bet1 = idealbet1
																bet2 = idealbet2
															bet12 = (bet1 * FairlayAsk) / FairlayAsk2
															bet21 = (bet2 * lay) / lay2
															if (bet12 * 1000) > 1:
																print 'bet1: ' + str(bet1)
																print 'bet1: ' + str(bet2)
																n1 = self.create_order(-1, contest['ID'], FairlayAsk, bet1, 0)
																quote2 = urllib.quote(name)
																quote = ('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote2 + '&odd=' + str(back) + '&stake=' + str(bet2) + '&bet_type=back')
																r5 = sessionBetBTC.post(quote)
																with open('ids.txt', 'a') as f:
																	f.write(str(theId) + '\n')
																time.sleep(60)
																print n1
																print r5.text
														
														
																#print 'if bet1 wins: ' + str(bet1) + ' * ' + str(FairlayAsk) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet1 * FairlayAsk - bet1 - bet2)
																#print 'if bet2 wins: ' + str(bet2) + ' * ' + str(back) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet2 * back - bet1 - bet2)
														else:
															print 2
															print theName
															print contest['Title']
															print w1
															bet1 = 1 / (w1 * FairlayBid)
														
															bet2 = 1 / (w1 * lay)
															bVol = layVol	
															print FairlayBid2
															print lay
															aVol = FairlayBidVol
															idealbet1 = (aVol + bVol) * bet1
															idealbet2 = (aVol + bVol) * bet2
															if idealbet1 > aVol:
																idealbet2 = (aVol / bet1) * bet2
																idealbet1 = aVol
															elif idealbet2 > bVol:
																idealbet1 = (bVol / bet2) * bet1
																idealbet2 = bVol
															print 'aVol: ' + str(aVol)
															print 'bVol: ' + str(bVol)
															print 'idealbet1: ' + str(idealbet1)
															print 'idealbet2: ' + str(idealbet2)
															if lowBal < idealbet1 or lowBal < idealbet2:
																idealbet1 = bet1 * lowBal
																idealbet2 = bet2 * lowBal
																bet1 = idealbet1
																bet2 = idealbet2
															else:
																bet1 = idealbet1
																bet2 = idealbet2
															print bet1
															print bet2
															bet12 = (bet1 * FairlayBid) / FairlayBid2
															bet21 = (bet2 * lay) / lay2
															if (bet12 * 1000) > 1:
																print 'bet1: ' + str(bet1)
																print 'bet1: ' + str(bet2)
																n1 = self.create_order(-1, contest['ID'], FairlayBid, bet1, 1)
																quote2 = urllib.quote(name)
																quote = ('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote2 + '&odd=' + str(lay) + '&stake=' + str(bet2) + '&bet_type=lay')
																r5 = sessionBetBTC.post(quote)
																print n1
																print r5.text
																with open('ids.txt', 'a') as f:
																	f.write(str(theId) + '\n')										
																time.sleep(60)
														
																#print 'if bet1 wins: ' + str(bet1) + ' * ' + str(FairlayBid2) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet1 * FairlayBid2 - bet1 - bet2)
																#print 'if bet2 wins: ' + str(bet2) + ' * ' + str(lay) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet2 * lay - bet1 - bet2)
								if name2 in contest['Ru'][0]['Name']: #donna
									if contest['_Type'] == 0 and contest['_Period'] == 2:
						
						
										FairlayBid = json.loads(contest['OrdBStr'][:-1])['Bids'][0][0]
										FairlayAsk = json.loads(contest['OrdBStr'][:-1])['Asks'][0][0]
										FairlayBidVol = json.loads(contest['OrdBStr'][:-1])['Bids'][0][1] / 1000
										FairlayAskVol = json.loads(contest['OrdBStr'][:-1])['Asks'][0][1] / 1000
										FairlayBid2 = 1 / (1 - (1 / FairlayBid))
										FairlayAsk2 = 1 / (1 - (1 / FairlayAsk))									
										print FairlayBid
										print FairlayAsk
										print FairlayBid2
										print FairlayAsk2
										betbtc= json.loads(r3.text)	
										for winner in betbtc:
											if name in winner:
												back = winner[name]['Back'][0][0]
												backVol = winner[name]['Back'][0][1]
												lay = winner[name]['Lay'][0][0]
												layVol = winner[name]['Lay'][0][1]
											
												if type(back) is float and type(lay) is float:
													back2 = 1 / (1 - (1 / back))
													lay2 = 1 / (1 - (1 / lay))
													w1 = (1 / float(FairlayBid)) + (1 / float(lay2))
													w2 = (1 / float(FairlayAsk2)) + (1 / float(back))
													if w1 < .9 and w1 > .6:
														if w2 < w1:
															print FairlayAskVol
															print backVol
															print 3
															print theName
															print contest['Title']
															print w2
															bet1 = 1 / (w2 * FairlayAsk2)	
														
															bet2 = 1 / (w2 * back)
															bVol = backVol	
															aVol = FairlayAskVol
															print FairlayAsk2
															print back
															idealbet1 = (aVol + bVol) * bet1
															idealbet2 = (aVol + bVol) * bet2
															if idealbet1 > aVol:
																idealbet2 = (aVol / bet1) * bet2
																idealbet1 = aVol
															elif idealbet2 > bVol:
																idealbet1 = (bVol / bet2) * bet1
																idealbet2 = bVol
															print 'aVol: ' + str(aVol)
															print 'bVol: ' + str(bVol)
															print 'idealbet1: ' + str(idealbet1)
															print 'idealbet2: ' + str(idealbet2)	
															if lowBal < idealbet1 or lowBal < idealbet2:
																idealbet1 = bet1 * lowBal
																idealbet2 = bet2 * lowBal
																bet1 = idealbet1
																bet2 = idealbet2
															else:
																bet1 = idealbet1
																bet2 = idealbet2
															bet12 = (bet1 * FairlayAsk) / FairlayAsk2
															bet21 = (bet2 * lay) / lay2
															if (bet12 * 1000) > 1:																										
																print 'bet1: ' + str(bet1)
																print 'bet1: ' + str(bet2)
																self.create_order(-1, contest['ID'], FairlayAsk, bet1, 0)
																quote2 = urllib.quote(name2)
																quote = ('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote2 + '&odd=' + str(back) + '&stake=' + str(bet2) + '&bet_type=back')
																r5 = sessionBetBTC.post(quote)
																with open('ids.txt', 'a') as f:
																	f.write(str(theId) + '\n')
																time.sleep(60)
																#print 'if bet1 wins: ' + str(bet1) + ' * ' + str(FairlayAsk) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet1 * FairlayAsk - bet1 - bet2)
																#print 'if bet2 wins: ' + str(bet2) + ' * ' + str(back) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet2 * back - bet1 - bet2)
														else:	
															print 4
															print FairlayBidVol	
															print layVol
															print theName
															print contest['Title']
															print w1
															bet1 = 1 / (w1 * FairlayBid)
														
															bet2 = 1 / (w1 * lay)
															bVol = layVol	
															aVol = FairlayBidVol
															print FairlayBid2
															print lay
															idealbet1 = (aVol + bVol) * bet1
															idealbet2 = (aVol + bVol) * bet2
															if idealbet1 > aVol:
																idealbet2 = (aVol / bet1) * bet2
																idealbet1 = aVol
															elif idealbet2 > bVol:
																idealbet1 = (bVol / bet2) * bet1
																idealbet2 = bVol
															print 'aVol: ' + str(aVol)
															print 'bVol: ' + str(bVol)
															print 'idealbet1: ' + str(idealbet1)
															print 'idealbet2: ' + str(idealbet2)
															if lowBal < idealbet1 or lowBal < idealbet2:
																idealbet1 = bet1 * lowBal
																idealbet2 = bet2 * lowBal
																bet1 = idealbet1
																bet2 = idealbet2
															else:
																bet1 = idealbet1
																bet2 = idealbet2
															bet12 = (bet1 * FairlayBid) / FairlayBid2
															bet21 = (bet2 * lay) / lay2
															if (bet12 * 1000) > 1:
														
																print 'bet1: ' + str(bet1)
																print 'bet1: ' + str(bet2)
																n1 = self.create_order(-1, contest['ID'], FairlayBid, bet1, 1)
																quote2 = urllib.quote(name2)
																quote = ('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote2 + '&odd=' + str(lay) + '&stake=' + str(bet2) + '&bet_type=lay')
																r5 = sessionBetBTC.post(quote)															
																with open('ids.txt', 'a') as f:
																	f.write(str(theId) + '\n')
																time.sleep(60)
																print n1
																print r5.text
																#print 'if bet1 wins: ' + str(bet1) + ' * ' + str(FairlayBid2) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet1 * FairlayBid2 - bet1 - bet2)
																#print 'if bet2 wins: ' + str(bet2) + ' * ' + str(lay) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet2 * lay - bet1 - bet2)
									
					elif contest[7] == 'Match Odds':
						r3 = sessionBetBTC.get('https://www.betbtc.co/api/market/?id=' + str(theId))
						if 'status' not in json.loads(r3.text)[0]:
							name = contest[6][0]['name'] #Adrian
							name2 = contest[6][1]['name'] #Milos
							#Fairlay
							sessionFairlay = requests.Session()
							r4 = sessionFairlay.get('http://31.172.83.181:8080/free/markets/{"Cat":2,"OnlyActive":true,"ToID":10000}')
							for contest in json.loads(r4.text):
								#print 
								if name in contest['Ru'][0]['Name']: #angel wins:
									if contest['_Type'] == 0 and contest['_Period'] == 1:
										if "Bids" in contest['OrdBStr']:
					
							
											FairlayBid = json.loads(contest['OrdBStr'][:-1])['Bids'][0][0]
											FairlayAsk = json.loads(contest['OrdBStr'][:-1])['Asks'][0][0]
											FairlayBidVol = json.loads(contest['OrdBStr'][:-1])['Bids'][0][1] / 1000
											FairlayAskVol = json.loads(contest['OrdBStr'][:-1])['Asks'][0][1] / 1000
											FairlayBid2 = 1 / (1 - (1 / FairlayBid))
											FairlayAsk2 = 1 / (1 - (1 / FairlayAsk))
											print FairlayBid
											print FairlayAsk
											print FairlayBid2
											print FairlayAsk2
											betbtc= json.loads(r3.text)	
											for winner in betbtc:
												if name in winner:
													back = winner[name]['Back'][0][0]
													backVol = winner[name]['Back'][0][1]
													lay = winner[name]['Lay'][0][0]
													layVol = winner[name]['Lay'][0][1]
													if type(back) is float and type(lay) is float:
													
														back2 = 1 / (1 - (1 / back))
														lay2 = 1 / (1 - (1 / lay))
														w1 = (1 / float(FairlayBid)) + (1 / float(lay2))
														w2 = (1 / float(FairlayAsk2)) + (1 / float(back))
														if w1 < .9 and w1 > .6:
															if w2 < w1:
															
																print 5
																print contest
																#print theContest
																print r3.text
																print theName
																print contest['Title']
																print w2
	
																bet1 = 1 / (w2 * FairlayAsk2)
															
																bet2 = 1 / (w2 * back)
																bVol = backVol	
																print FairlayAsk2
																print back
																aVol = FairlayAskVol
																idealbet1 = (aVol + bVol) * bet1
																idealbet2 = (aVol + bVol) * bet2
																print '1st idealbet1: ' + str(idealbet1)
																print '1st idealbet2: ' + str(idealbet2)



																if idealbet1 > aVol:
																	idealbet2 = (aVol / bet1) * bet2
																	idealbet1 = aVol
																elif idealbet2 > bVol:
																	idealbet1 = (bVol / bet2) * bet1
																	idealbet2 = bVol
																print 'aVol: ' + str(aVol)
																print 'bVol: ' + str(bVol)
																print 'idealbet1: ' + str(idealbet1)
																print 'idealbet2: ' + str(idealbet2)
	
																if lowBal < idealbet1 or lowBal < idealbet2:
																	idealbet1 = bet1 * lowBal
																	idealbet2 = bet2 * lowBal
																	bet1 = idealbet1
																	bet2 = idealbet2
																else:
																	bet1 = idealbet1
																	bet2 = idealbet2
	#bet1: 0.468817204301 # 0.2848717 / 0.195981132
	#bet2: 0.531182795699 # 0.3212383 / .221 = 1.453566968
	#0.38511 # 0.1810017
																								
																bet12 = (bet1 * FairlayAsk) / FairlayAsk2
																bet21 = (bet2 * lay) / lay2
	#0.221 # 0.11713 / .221														print FairlayAsk
	#															print back
																if (bet12 * 1000) > 1:
														
																	n1 = self.create_order(-1, contest['ID'], FairlayAsk, bet1, 0)
																	print n1
																	quote2 = urllib.quote(name)
																	quote =('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote2 + '&odd=' + str(back) + '&stake=' + str(bet2) + '&bet_type=back')
																	r5 = sessionBetBTC.post(quote)
																	print r5.text
																	with open('ids.txt', 'a') as f:
																		f.write(str(theId) + '\n')
																	time.sleep(60)
																	print 'bet1: ' + str(bet1)
																	print 'bet1: ' + str(bet2)
																	#print 'if bet1 wins: ' + str(bet1) + ' * ' + str(FairlayAsk) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet1 * FairlayAsk - bet1 - bet2)
																	#print 'if bet2 wins: ' + str(bet2) + ' * ' + str(back) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet2 * back - bet1 - bet2)
															else:
																print FairlayBidVol
																print layVol
																print 6
																print theName
																print contest['Title']
																print w1
																bet1 = 1 / (w1 * FairlayBid)
															
															
																bet2 = 1 / (w1 * lay)
																bVol = layVol	
																print FairlayBid2
																print lay
																aVol = FairlayBidVol
																idealbet1 = (aVol + bVol) * bet1
																idealbet2 = (aVol + bVol) * bet2
																if idealbet1 > aVol:
																	idealbet2 = (aVol / bet1) * bet2
																	idealbet1 = aVol
																elif idealbet2 > bVol:
																	idealbet1 = (bVol / bet2) * bet1
																	idealbet2 = bVol
																print 'aVol: ' + str(aVol)
																print 'bVol: ' + str(bVol)
																print 'idealbet1: ' + str(idealbet1)
																print 'idealbet2: ' + str(idealbet2)
																if lowBal < idealbet1 or lowBal < idealbet2:
																	idealbet1 = bet1 * lowBal
																	idealbet2 = bet2 * lowBal
																	bet1 = idealbet1
																	bet2 = idealbet2
																else:
																	bet1 = idealbet1
																	bet2 = idealbet2
																bet12 = (bet1 * FairlayBid) / FairlayBid2
																bet21 = (bet2 * lay) / lay2
																if (bet12 * 1000) > 1:
																	n1 = self.create_order(-1, contest['ID'], FairlayBid, bet1, 1)
																	print n1
																	quote = urllib.quote(name)
																	quote2 = ('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote + '&odd=' + str(lay) + '&stake=' + str(bet2) + '&bet_type=lay')
																	print ('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote + '&odd=' + str(lay) + '&stake=' + str(bet2) + '&bet_type=lay')
																	r5 = sessionBetBTC.post(quote2)
																	print r5.text
																	with open('ids.txt', 'a') as f:
																		f.write(str(theId) + '\n')
																	time.sleep(60)
																	print 'bet1: ' + str(bet1)
																	print 'bet1: ' + str(bet2)
																	#print 'if bet1 wins: ' + str(bet1) + ' * ' + str(FairlayBid2) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet1 * FairlayBid2 - bet1 - bet2)
																	#print 'if bet2 wins: ' + str(bet2) + ' * ' + str(lay) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet2 * lay - bet1 - bet2)		
								if name2 in contest['Ru'][0]['Name']: #donna wins:
									if contest['_Type'] == 0 and contest['_Period'] == 1:
										if "Bids" in contest['OrdBStr']:
					
							
											FairlayBid = json.loads(contest['OrdBStr'][:-1])['Bids'][0][0]
											FairlayAsk = json.loads(contest['OrdBStr'][:-1])['Asks'][0][0]
											FairlayBidVol = json.loads(contest['OrdBStr'][:-1])['Bids'][0][1] / 1000
											FairlayAskVol = json.loads(contest['OrdBStr'][:-1])['Asks'][0][1] / 10002
											FairlayBid2 = 1 / (1 - (1 / FairlayBid))
											FairlayAsk2 = 1 / (1 - (1 / FairlayAsk))
											print FairlayBid
											print FairlayAsk
											print FairlayBid2
											print FairlayAsk2
											betbtc= json.loads(r3.text)	
											for winner in betbtc:
												if name in winner:
													back = winner[name]['Back'][0][0]
													backVol = winner[name]['Back'][0][1]
													lay = winner[name]['Lay'][0][0]
													layVol = winner[name]['Lay'][0][1]
												
													if type(back) is float and type(lay) is float:
														back2 = 1 / (1 - (1 / back))
														lay2 = 1 / (1 - (1 / lay))
														w1 = (1 / float(FairlayBid)) + (1 / float(lay2))
														w2 = (1 / float(FairlayAsk2)) + (1 / float(back))
														if w1 < .9 and w1 > .6:
															if w2 < w1:
																print FairlayAskVol
																print backVol
																print 7
																print theName
																print contest['Title']
																print 
																print w2
																bet1 = 1 / (w2 * FairlayAsk2)
															
																bet2 = 1 / (w2 * back)	
																bVol = backVol	
																aVol = FairlayAskVol
																print FairlayAsk2
																print back
																idealbet1 = (aVol + bVol) * bet1
																idealbet2 = (aVol + bVol) * bet2
																if idealbet1 > aVol:
																	idealbet2 = (aVol / bet1) * bet2
																	idealbet1 = aVol
																elif idealbet2 > bVol:
																	idealbet1 = (bVol / bet2) * bet1
																	idealbet2 = bVol
																print 'aVol: ' + str(aVol)
																print 'bVol: ' + str(bVol)
																print 'idealbet1: ' + str(idealbet1)
																print 'idealbet2: ' + str(idealbet2)
																if lowBal < idealbet1 or lowBal < idealbet2:
																	idealbet1 = bet1 * lowBal
																	idealbet2 = bet2 * lowBal
																	bet1 = idealbet1
																	bet2 = idealbet2
																else:
																	bet1 = idealbet1
																	bet2 = idealbet2
																bet12 = (bet1 * FairlayAsk) / FairlayAsk2
																bet21 = (bet2 * lay) / lay2
																if (bet12 * 1000) > 1:
																	n1 = self.create_order(-1, contest['ID'], FairlayAsk, bet1, 0)
																	print n1
																	quote2 = urllib.quote(name2)
																	quote = ('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote2 + '&odd=' + str(back) + '&stake=' + str(bet2) + '&bet_type=back')
																	r5 = sessionBetBTC.post(quote)
																	print r5.text
																	with open('ids.txt', 'a') as f:
																		f.write(str(theId) + '\n')
																	time.sleep(60)
																	print 'bet1: ' + str(bet1)
																	print 'bet1: ' + str(bet2)
																	#print 'if bet1 wins: ' + str(bet1) + ' * ' + str(FairlayAsk) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet1 * FairlayAsk - bet1 - bet2)
																	#print 'if bet2 wins: ' + str(bet2) + ' * ' + str(back) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet2 * back - bet1 - bet2)
															else:
																print 8
																print FairlayBidVol
																print layVol
																print theName
																print contest['Title']
																print w1
																bet1 = 1 / (w1 * FairlayBid)
															
																bet2 = 1 / (w1 * lay)
																bVol = layVol
																print FairlayBid2
																print lay	
																aVol = FairlayBidVol
																idealbet1 = (aVol + bVol) * bet1
																idealbet2 = (aVol + bVol) * bet2
																if idealbet1 > aVol:
																	idealbet2 = (aVol / bet1) * bet2
																	idealbet1 = aVol
																elif idealbet2 > bVol:
																	idealbet1 = (bVol / bet2) * bet1
																	idealbet2 = bVol
																print 'aVol: ' + str(aVol)
																print 'bVol: ' + str(bVol)
																print 'idealbet1: ' + str(idealbet1)
																print 'idealbet2: ' + str(idealbet2)
																if lowBal < idealbet1 or lowBal < idealbet2:
																	idealbet1 = bet1 * lowBal
																	idealbet2 = bet2 * lowBal
																	bet1 = idealbet1
																	bet2 = idealbet2
																else:
																	bet1 = idealbet1
																	bet2 = idealbet2
																bet12 = (bet1 * FairlayBid) / FairlayBid2
																bet21 = (bet2 * lay) / lay2
																if (bet12 * 1000) > 1:
																	n1 = self.create_order(-1, contest['ID'], FairlayBid, bet1, 1)
																	print n1
																	quote2 = urllib.quote(name2)
																	quote = ('https://www.betbtc.co/api/bet/?market_id=' + str(theId) + '&selection=' + quote2 + '&odd=' + str(lay) + '&stake=' + str(bet2) + '&bet_type=lay')
																	r5 = sessionBetBTC.post(quote)
																	print r5.text
																	with open('ids.txt', 'a') as f:
																		f.write(str(theId) + '\n')
																	time.sleep(60)	
																	print 'bet1: ' + str(bet1)
																	print 'bet1: ' + str(bet2)
																	#print 'if bet1 wins: ' + str(bet1) + ' * ' + str(FairlayBid2) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet1 * FairlayBid2 - bet1 - bet2)
																	#print 'if bet2 wins: ' + str(bet2) + ' * ' + str(lay) + ' - ' + str(bet1) + ' - ' + str(bet2) + ' = ' + str(bet2 * lay - bet1 - bet2)
			except Exception as e:
				print e	
matching = FairlayOrderMatching()

#print matching.create_wait_get_matched()
# print matching.calculate_position(82339763895)
