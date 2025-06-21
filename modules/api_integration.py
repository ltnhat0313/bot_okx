# File: modules/api_integration.py

import requests
import json
import hmac
import base64
import time
import datetime
import logging

logger = logging.getLogger(__name__)

class OKXIntegration:
    def __init__(self, api_key, secret_key, passphrase, is_test=False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.is_test = is_test
        self.base_url = "https://www.okx.com"

    def _get_timestamp(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        return now_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def _sign(self, timestamp, method, request_path, body=''):
        if isinstance(body, dict):
            body = json.dumps(body)
        message = timestamp + method.upper() + request_path + body
        mac = hmac.new(bytes(self.secret_key, encoding='utf8'), bytes(message, encoding='utf8'), digestmod='sha256')
        d = mac.digest()
        return base64.b64encode(d).decode('utf-8')

    def _get_headers(self, method, request_path, body=''):
        timestamp = self._get_timestamp()
        headers = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self._sign(timestamp, method, request_path, body),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
        }
        if self.is_test:
            headers['x-simulated-trading'] = '1'
        return headers

    def get_klines(self, instId, bar='1h', total_candles=300):
        all_klines_data = []
        limit_per_call = 300 
        num_calls = (total_candles + limit_per_call - 1) // limit_per_call
        before_ts = ''
        for _ in range(num_calls):
            request_path = f"/api/v5/market/history-candles?instId={instId}&bar={bar}&limit={limit_per_call}"
            if before_ts:
                request_path += f"&before={before_ts}"
            method = 'GET'
            headers = self._get_headers(method, request_path)
            try:
                response = requests.get(self.base_url + request_path, headers=headers)
                response.raise_for_status()
                json_response = response.json()
                if json_response.get('code') == '0' and json_response.get('data'):
                    data = json_response['data']
                    logger.info(f"Successfully fetched {len(data)} klines for {instId}")
                    all_klines_data = data + all_klines_data
                    if data: before_ts = data[-1][0]
                    else: break 
                else:
                    logger.warning(f"API call successful but no data returned. Response: {json_response}")
                    break
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching klines for {instId}: {e}")
                return None
        return {'code': '0', 'msg': '', 'data': all_klines_data}

    def get_instrument_details(self, instId):
        request_path = f"/api/v5/public/instruments?instType=SWAP&instId={instId}"
        headers = {'Content-Type': 'application/json'}
        if self.is_test: headers['x-simulated-trading'] = '1'
        try:
            response = requests.get(self.base_url + request_path, headers=headers)
            response.raise_for_status()
            json_response = response.json()
            if json_response.get('code') == '0' and json_response.get('data'):
                return json_response['data'][0]
            else:
                logger.error(f"Could not get instrument details for {instId}. Response: {json_response}")
                return None
        except Exception as e:
            logger.error(f"Exception getting instrument details for {instId}: {e}")
            return None

    def get_account_balance(self, ccy='USDT'):
        request_path = f"/api/v5/account/balance?ccy={ccy}"
        method = 'GET'
        headers = self._get_headers(method, request_path)
        try:
            response = requests.get(self.base_url + request_path, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get('code') == '0' and data.get('data') and data['data'][0].get('details'):
                balance = float(data['data'][0]['details'][0]['availBal'])
                logger.info(f"Available balance for USDT: {balance:,.2f}")
                return balance
            logger.warning(f"Could not parse balance from response: {data}")
            return None
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return None

    def set_leverage(self, instId, lever, mgnMode='cross', posSide='long'):
        """Tự động thiết lập đòn bẩy."""
        request_path = "/api/v5/account/set-leverage"
        method = 'POST'
        body = {"instId": instId, "lever": str(lever), "mgnMode": mgnMode, "posSide": posSide}
        headers = self._get_headers(method, request_path, body)
        try:
            response = requests.post(self.base_url + request_path, headers=headers, data=json.dumps(body))
            response.raise_for_status()
            json_response = response.json()
            if json_response.get('code') == '0' and json_response.get('data'):
                logger.info(f"Successfully set leverage for {instId} to {lever}x.")
                return json_response['data'][0]
            else:
                logger.error(f"Failed to set leverage. API Response: {json_response}")
                return None
        except Exception as e:
            logger.error(f"Exception setting leverage: {e}")
            return None

    def place_order(self, instId, side, ordType, sz):
        """Đặt lệnh giao dịch."""
        request_path = "/api/v5/trade/order"
        method = 'POST'
        body = {
            "instId": instId, "tdMode": "cross", "side": side,
            "ordType": ordType, "sz": str(sz), "posSide": "long"
        }
        headers = self._get_headers(method, request_path, body)
        try:
            response = requests.post(self.base_url + request_path, headers=headers, data=json.dumps(body))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None