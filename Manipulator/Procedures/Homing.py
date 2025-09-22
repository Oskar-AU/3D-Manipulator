from .. import IO
import logging
from TurnOn import turn_on

logger = logging.getLogger(__name__)


def home(driver: IO.Driver):
    """
    Sends a command to home the LinMot motors.
    """
    datagram = IO.linUDP()
    turn_on(driver)
    home_request = IO.Request(IO.Response(state_var=True), IO.Control_Word(switch_on=True, home=True))
    
    translated_response = datagram.sendto(home_request, driver)
    
    while not translated_response.get('state_var').get('homing_finished'):
        status_request = IO.Request(IO.Response(state_var=True))
        translated_response = datagram.sendto(status_request, driver)
    
    home_off_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True))
    datagram.sendto(home_off_request, driver)
    logger.info("Homing procedure completed.")
if __name__ == "__main__":
    home()