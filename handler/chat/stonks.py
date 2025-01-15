from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import getLogger
from os import environ

from simone.handlers import Registry, session


def emojify_number(value):
    # TODO: translate
    return (
        str(value)
        .replace('0', ':zero:')
        .replace('1', ':one:')
        .replace('2', ':two:')
        .replace('3', ':three:')
        .replace('4', ':four:')
        .replace('5', ':five:')
        .replace('6', ':six:')
        .replace('7', ':seven:')
        .replace('8', ':eight:')
        .replace('9', ':nine:')
        .replace('.', ':black_circle_for_record:')
        .replace('-', ':heavy_minus_sign:')
        .replace('+', ':heavy_plus_sign:')
        .replace('%', ':percent:')
    )


def plus_or_minus(value):
    value = str(value)
    if value[0] != '-':
        return f'+{value}'
    return value


def round_to_cents(value):
    return int(100 * value) / 100.0


# TODO: explore https://finnhub.io/register
class Stonks(object):
    '''
    Stonk quotes

    To get stonk quotes:
      .stonks tsla
      .stonks btc

    To get stock quotes:
      .stocks tsla
      .stocks btc
    '''

    log = getLogger('Stonks')

    WSJ_URL = 'https://api.wsj.net/api/dylan/quotes/v2/comp/quoteByDialect'
    WSJ_NAMESPACES = (
        'STOCK/US/XNAS',  # NASDAQ individual stocks
        'STOCK/US/XNYS',  # NYSE individual stocks
        'FUND/US/BATS',  # BATS funds
        'FUND/US/ARCX',  # ARCX funds
        'FUND/UK/XLON',  # London funds
        'FUND/US/XNAS',  # NASDAQ funds
        'STOCK/US/OOTC',  # US OTC individual stocks
        'CURRENCY/US/XTUP',  # Currencies
        'CRYPTOCURRENCY/US/CoinDesk',  # Cryptocurrencies
        'FUTURE/US/XCBT',  # US Commodity Futures
    )
    WSJ_ALIASES = {
        'DJIA': 'INDEX/US/Dow Jones Global/DJIA',
        'DJI': 'INDEX/US/Dow Jones Global/DJIA',
        'SPX': 'INDEX/US/S&P US/SPX',
        'SP500': 'INDEX/US/S&P US/SPX',
        'NASDAQ': 'INDEX/US/XNAS/COMP',
        'OIL': 'FUTURE/US/XNYM/CL.1',
        'CAD': 'CURRENCY/US/XTUP/CADUSD',
        'EUR': 'CURRENCY/US/XTUP/EURUSD',
        'AUD': 'CURRENCY/US/XTUP/AUDUSD',
        'BITCOIN': 'CRYPTOCURRENCY/US/CoinDesk/BTCUSD',
        'BTC': 'CRYPTOCURRENCY/US/CoinDesk/BTCUSD',
    }

    def __init__(
        self, alpha_vantage_key, wsj_quotes_ckey, wsj_quotes_entitlement_token
    ):
        self.alpha_vantage_key = alpha_vantage_key
        self.wsj_quotes_ckey = wsj_quotes_ckey
        self.wsj_quotes_entitlement_token = wsj_quotes_entitlement_token

        self._executor = ThreadPoolExecutor()

    def config(self):
        return {'commands': ('stocks', 'stonks')}

    def lookup_wsj(self, text):
        text = text.replace('-', '.')
        if '/' in text:
            # try an exact match
            id_param = text
        else:
            try:
                id_param = self.WSJ_ALIASES[text]
                self.log.debug('alias id_param=%s', id_param)
            except KeyError:
                namespaced = [f'{tok}/{text}' for tok in self.WSJ_NAMESPACES]
                id_param = ','.join(namespaced)
                self.log.debug('namespaced id_param=%s', id_param)

        resp = session.get(
            self.WSJ_URL,
            params={
                'EntitlementToken': self.wsj_quotes_entitlement_token,
                'MaxInstrumentMatches': '1',
                'accept': 'application/json',
                'ckey': self.wsj_quotes_ckey,
                'dialect': 'charting',
                'id': id_param,
                'needed': 'CompositeTrading',
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return (None, None, None)
        data = resp.json()
        for ir in data.get('InstrumentResponses', []):
            try:
                ct = ir['Matches'][0]['CompositeTrading']
                open_value = round_to_cents(ct['Open']['Value'])
                last_value = round_to_cents(ct['Last']['Price']['Value'])
                change = round_to_cents(ct['NetChange']['Value'])
                return (open_value, last_value, change)
            except (IndexError, KeyError):
                pass

        return (None, None, None)

    def lookup_crypto(self, text):
        url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'DIGITAL_CURRENCY_DAILY',
            'symbol': text,
            'market': 'USD',
            'apikey': self.alpha_vantage_key,
        }
        resp = session.get(url, params=params)
        if resp.status_code != 200:
            self.log.error(
                'lookup_crypto: request failed, code=%d, content=%s',
                resp.status_code,
                resp.content,
            )
            return (None, None, None)
        data = resp.json()
        error = data.get('Error Message', None)
        if error:
            self.log.debug('lookup_crypto: error=%s', error)
            return (None, None, None)
        data = data['Time Series (Digital Currency Daily)']
        dates = data.keys()
        dates = sorted(dates, reverse=True)
        # most recent
        latest = data[dates[0]]
        open_value = float(latest['1. open'])
        last_value = float(latest['4. close'])
        return (open_value, last_value, last_value - open_value)

    def lookup(self, text):
        wsj = self._executor.submit(self.lookup_wsj, text)
        crypto = self._executor.submit(self.lookup_crypto, text)
        for future in as_completed((wsj, crypto)):
            open_value, last_value, change = future.result()
            if open_value is not None:
                return (open_value, last_value, change)
        # nobody had an answer
        return (None, None, None)

    def stonks(self, context, text, open_value, last_value, change, change_pct):
        if open_value is None:
            context.say(
                f"I couldn't find the price for `{text}` so I'll just go ahead and assume it's NOT STONKS :not_stonks:"
            )
            return
        response = f'`{text}` is '
        if change > 0:
            response += ' STONKS :stonks:'
        else:
            response += ' NOT STONKS :not_stonks:'

        response += (
            '\n'
            + emojify_number(last_value)
            + ' ('
            + emojify_number(plus_or_minus(change))
            + ') ('
            + emojify_number(plus_or_minus(change_pct) + '%')
            + ')'
        )
        context.say(response)

    def stocks(self, context, text, open_value, last_value, change, change_pct):
        if open_value is None:
            context.say(f"I couldn't find the price for `{text}`")
            return
        context.say(
            f'`{text}`: {last_value} ({plus_or_minus(change)}) ({plus_or_minus(change_pct)}%)'
        )

    def command(self, context, command, text, **kwargs):
        text = text.upper()
        if text in self.WSJ_ALIASES:
            # special case go straight to WSJ
            self.log.debug('command: wsj specific')
            open_value, last_value, change = self.lookup_wsj(text)
        else:
            self.log.debug('command: trying all')
            open_value, last_value, change = self.lookup(text)

        change_pct = round(100 * (change / open_value), 2)

        if command == 'stonks':
            self.stonks(
                context, text, open_value, last_value, change, change_pct
            )
        else:
            self.stocks(
                context, text, open_value, last_value, change, change_pct
            )


alpha_vantage_key = environ['ALPHA_VANTAGE_KEY']
wsj_quotes_ckey = environ['WSJ_QUOTES_CKEY']
wsj_quotes_entitlement_token = environ['WSJ_QUOTES_ENTITLEMENT_TOKEN']

Registry.register_handler(
    Stonks(alpha_vantage_key, wsj_quotes_ckey, wsj_quotes_entitlement_token)
)
