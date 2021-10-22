from os import environ

from simone.handlers import Registry, session


class Weather(object):
    '''
    Get the current weather

    To get the weather for a city
      .weather <city name>
    '''

    URL = 'https://api.openweathermap.org/data/2.5/weather'

    def __init__(self, app_id):
        self.app_id = app_id

    def config(self):
        return {'commands': ('weather',)}

    def _weather_icon(self, data):
        try:
            weather = data['weather'][0]
            # Unfortunately only paid workspaces allow bots to upload emoji so
            # these have to be manually added. See script/weather-emoji
            return f':weather-{weather["icon"]}: - {weather["description"]}'
        except (IndexError, KeyError):
            return ''

    def command(self, context, text, **kwargs):
        n = len(text)
        text = text.replace('in celsius', '')
        # If it's shorter we found it and they want C
        in_c = n != len(text)

        params = {
            'q': text,
            'appid': self.app_id,
            'units': 'celsius' if in_c else 'imperial',
        }
        resp = session.get(self.URL, params=params)
        if resp.status_code == 404:
            # unknown location/city
            context.say(f"Sorry. I wasn't able to find weather for `{text}`")
            return
        resp.raise_for_status()
        data = resp.json()
        main = data['main']
        temp = main['temp']
        feels_like = main['feels_like']
        humidity = main['humidity']
        weather_icon = self._weather_icon(data)
        unit = 'C' if in_c else 'F'
        context.say(
            f'Current weather for `{text}`: {temp}{unit}, feels like {feels_like}{unit}. {humidity}% humidity. {weather_icon}'
        )


app_id = environ['OPEN_WEATHER_MAP_APP_ID']
Registry.register_handler(Weather(app_id))
