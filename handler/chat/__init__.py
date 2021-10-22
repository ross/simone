# pulled in so that other handlers can include them from here for conveience
from simone.handlers import Registry, session

from .echo import Echo
from .greetings import Greetings
from .help import Help
from .joke import Joke
from .ping import Ping
from .quote import Quote
from .wave import Wave
from .weather import Weather


# Quell warnings
Registry
session
Echo
Greetings
Help
Joke
Ping
Quote
Wave
Weather
