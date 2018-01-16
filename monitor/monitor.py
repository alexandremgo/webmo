from peewee import OperationalError
import signal
import sys

from monitor.models import Website, Check, Alert
from monitor.monitor_tui import TerminalController

# Keep a reference in order to properly exit the program
terminal_controller = None


def main():
    """Main function of the monitoring program"""
    global terminal_controller

    # Start by initiate our sqlite database:
    db_init()
    # Then initiate the urwid/TUI loop to render our terminal
    terminal_controller = TerminalController()
    terminal_controller.main()


def db_init():
    """Init the database

    Create the tables associated to our Website and Check models
    """

    # Create the tables only if they don't already exist
    if not Website.table_exists():
        Website.create_table()

    if not Check.table_exists():
        Check.create_table()

    if not Alert.table_exists():
        Alert.create_table()


def exit_program(signal, frame):
    """Terminate the program by calling exit_program from the instance of TerminalController
    in order to stop the several threads/schedulers
    """
    global terminal_controller

    if terminal_controller:
        terminal_controller.exit_program()

    sys.exit(0)


# Call exit_program when the program is exiting
signal.signal(signal.SIGINT, exit_program)

# start only if monitor.py has been executing (and not importing)
if __name__ == '__main__':
    main()
