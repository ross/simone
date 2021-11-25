# pulled in so that other handlers can include them from here for conveience
from simone.handlers import Registry, session

from .advice import Advice
from .echo import Echo
from .greetings import Greetings
from .help import Help
from .holidays import Holidays
from .images import Images, Kittens, Puppies
from .joke import Joke
from .ping import Ping
from .quote import Quote
from .random import Coin, Dice, EightBall
from .stonks import Stonks
from .trash_talk import TrashTalk
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
Holidays
Images
Joke
Kittens
Ping
Puppies
Quote
Stonks
TrashTalk
Wave
Weather
