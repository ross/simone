# pulled in so that other handlers can include them from here for conveience
from simone.handlers import Registry, session

from .advice import Advice
from .echo import Echo
from .greetings import Greetings
from .help import Help
from .joke import Joke
from .ping import Ping
from .quote import Quote
from .random import Coin, Dice, EightBall
from .stonks import Stonks
from .sup import Sup
from .wave import Wave
from .weather import Weather


# Quell warnings
Registry
session
Advice
Coin
Dice
Echo
EightBall
Greetings
Help
Joke
Ping
Quote
Stonks
Sup
Wave
Weather
