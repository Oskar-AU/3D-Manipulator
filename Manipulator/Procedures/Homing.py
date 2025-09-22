import IO

def home(driver: Driver):
    """
    Sends a command to home the LinMot motors.
    """
    datagram = IO.linUDP()
    # Create a response and control word with home and switch_on set to True
    response = IO.Response()
    control = IO.Control_Word(switch_on=True, home=True)
    IO.Request(response, control)

    # Create a response and control word with home and switch_on set to False
    response = IO.Response()
    control = IO.Control_Word(switch_on=True)
    IO.Request(response, control)

if __name__ == "__main__":
    home()