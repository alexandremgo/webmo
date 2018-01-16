"""Terminal User Interface classes"""

import urwid
from time import time, strftime, localtime
import math

from .websites_settings import SettingsPopUp, DisplaySettings
from .models import Website, Alert
from .website_monitor import WebsiteMonitor

blank = urwid.Divider()  # A blank line
vline = urwid.AttrWrap(urwid.SolidFill(u'\u2502'), 'line')
hline = urwid.AttrWrap(urwid.SolidFill(u'\u2015'), 'line')
date_format = "%d/%m/%Y %H:%M:%S"


class SelectableText(urwid.Edit):
    """An Edit text that imitate a urwid.Text that can be select by the cursor"""

    def valid_char(self, ch):
        # If return False nothing can be put in the input field
        return False


class ExtendedListBox(urwid.ListBox):
    """Listbow widget with customed keypress actions"""

    def keypress(self, size, key):

        # to the top
        if key in ('t', 'T'):
            self.scroll_to_top()
            key = None
        # to the bottom
        elif key in ('b', 'B'):
            self.scroll_to_bottom()
            # Select the last selectable element (SelectableText) by simulating a up
            # otherwise it would not be focus on a selectable element
            key = 'up'
        # page up: move cursor up one listbox length
        elif key in ('u', 'U'):
            self._keypress_page_up(size)
        # page down: move cursor down one listbox length
        elif key in ('d', 'D'):
            self._keypress_page_down(size)

        super(ExtendedListBox, self).keypress(size, key)
        return key

    def scroll_to_top(self):
        """Scrolling to the top by changing the focus to the element at position 0"""
        self.set_focus(0)

    def scroll_to_bottom(self):
        """Scrolling to the bottom by changing the focus to the element at the last position"""
        self.set_focus(len(self.body) - 1)


class MainView(urwid.WidgetWrap):
    """The frame view that will wrap all the widget of the program"""

    # Signals that MainView instances can emit
    signals = ['exit', 'exit_settings']

    # Design attributes: list of (name, like_other_name)
    # or (name, foreground, background, mono, foreground_high, background_high)
    # Attributes ending by "_f" is an attribute design when the element has the focus
    palette = [
        ('body', 'light gray', 'black', 'standout'),
        ('header', 'light cyan', 'black', 'bold'),
        ('footer', 'light cyan', 'black', 'bold'),
        ('line', 'light gray', 'black', 'standout'),
        ('alert_down', 'light red', 'black'),
        ('alert_down_f', 'white', 'dark red'),
        ('alert_recovered', 'dark green', 'black'),
        ('alert_recovered_f', 'white', 'dark green'),
        ('reversed', 'standout', ''),
        ('check_box', 'light cyan', 'black'),
        ('check_box_f', 'black', 'dark cyan'),
        ('stats_date', 'light magenta', 'black'),
        ('stats_date_f', 'white', 'dark magenta'),
        ('button', 'light cyan', 'black'),
        ('button_f', 'black', 'dark cyan'),
        ('url', 'light magenta', 'black'),
        ('url_f', 'white', 'dark magenta'),
        ('main_shadow', 'dark cyan', 'black'),
        ('input', 'light cyan', 'black'),
        ('input_f', 'black', 'dark cyan'),
        ('submit_confirmation', 'light green', 'black')

    ]

    DIGITS = 1  # number of digits to display for the stats
    ARRAY_WIDTH = 8  # number of unit columns representing the width of 1 column of the array status codes count

    def __init__(self, controller, monitors):
        # The TerminalController instance and its monitors
        self.controller = controller
        self.monitors = monitors  # at init, monitors is None

        # The widget containing the real-time stats
        self.stats_w = None
        # The widget containing the alerts history
        self.history_w = None
        # The widget containing the button for the settings menu
        self.menu_w = None
        # The SettingsPopUp instance
        self.pop_up_settings = None
        # The date of the last alert in order to now from which alert to update the history
        self.date_last_alert = 0
        # The settings widget displayed to enable and disable websites
        self.display_settings = DisplaySettings(self.monitors)

        urwid.WidgetWrap.__init__(self, self.main_window())

    def history_window(self):
        """Set up the widget where checks appear and return the "window"
        (a frame around the widget) that will be displayed

        """
        self.history_w = ExtendedListBox(urwid.SimpleListWalker([
            SelectableText("Beginning of the alerts")
        ]))
        self.update_alert_history()

        return urwid.Frame(self.history_w, footer=self.shortcuts_footer())

    def display_alert(self, alert):
        """Return a urwid.Pile displaying the alert (down or recovered)"""
        content = []
        if alert.availability < 80:
            content.append(urwid.AttrMap(
                SelectableText("Website " + alert.website.url + " is down. Availability = " +
                               str(alert.availability) + "%, since " +
                               self.date_last_alert.strftime(date_format)
                               ), "alert_down", "alert_down_f"))
        elif alert.availability >= 80:
            content.append(urwid.AttrMap(
                SelectableText("Website " + alert.website.url + " has recovered. Availability = " +
                               str(alert.availability) + "%, since " +
                               self.date_last_alert.strftime(date_format)
                               ), "alert_recovered", "alert_recovered_f"))

        content.append(blank)
        return urwid.Pile(content)

    def get_alert_history(self):
        """Different from update because the query order is desc and the alert is appended"""

        # Keep the where, if decide to change self.date_last_alert later to take only some alerts
        query = Alert.select(Alert, Website).join(Website).where(Alert.date > self.date_last_alert).order_by(
            Alert.date.desc())

        content = []

        if query.exists():
            for alert in query:
                # The last alert in order to now from which alert to update the history
                self.date_last_alert = alert.date
                content.append(self.display_alert(alert))

        self.history_w.body.extend(content)

    def update_alert_history(self):
        """The new alerts are insert at the beginning. Normally it is called just for one more alert"""

        # Join to not do a extra query when we want the url of the website associated to the current alert
        query = Alert.select(Alert, Website).join(Website).where(Alert.date > self.date_last_alert).order_by(
            Alert.date)
        body = self.history_w.body

        if query.exists():
            for alert in query:
                # The last alert in order to now from which alert to update the history
                self.date_last_alert = alert.date
                body.insert(0, self.display_alert(alert))

    @staticmethod
    def shortcuts_footer():
        return urwid.AttrMap(urwid.Columns([
            urwid.Text("Shortcuts: t = top | b = bottom | u = page up | d = page down")
        ]), 'footer')

    def stats_window(self):
        """Set up the widget where checks appear and return the "window"
        (a frame around the widget) that will be displayed

        """
        # Keep a reference to the ExtendedListBox to update content
        self.stats_w = ExtendedListBox(body=urwid.SimpleFocusListWalker([
            SelectableText("Beginning ot the stats")
        ]))

        return urwid.Frame(self.stats_w, footer=self.shortcuts_footer())

    def menu_window(self):
        """Set up the menu widget and return the "window" (here it's the same as the widget)
        that will be displayed

        """
        # Settings for the websites that are being monitored
        self.pop_up_settings = SettingsPopUp(urwid.Button("Open websites settings"))

        # Forward the exit_settings signal
        urwid.connect_signal(self.pop_up_settings, 'exit_settings', lambda element: self._emit('exit_settings'))

        # Open the settings when the user open the app
        self.pop_up_settings.open_pop_up()

        # Later: more settings
        self.menu_w = urwid.ListBox(urwid.SimpleListWalker([
            blank,
            urwid.Padding(urwid.AttrMap(self.pop_up_settings, "button", "button_f"), width=26),
            blank,
            urwid.Text("Enable/Disable stats displaying:"),
            blank,
            self.display_settings
        ]))

        return self.menu_w

    def array_status_codes(self, codes_count):
        """Display status codes counts in an array"""

        # The vertical and horizontal separator to display the array
        vline_box = urwid.BoxAdapter(vline, height=1)
        hline_box = urwid.BoxAdapter(hline, height=1)

        # Left "column"
        content_left = [
            hline_box,
            urwid.Text("Status"),
            hline_box,
        ]

        # Right "column"
        content_right = [
            hline_box,
            urwid.Text("Counts"),
            hline_box,
        ]

        # right, middle and left separators
        content_vertical = [
            vline_box,
            vline_box,
            vline_box,
        ]

        if codes_count:
            for code, nb in codes_count.items():
                content_left.extend([
                    urwid.Text(str(code)),
                    hline_box,
                ])

                content_vertical.append(vline_box)

                content_right.extend([
                    urwid.Text(str(nb)),
                    hline_box,
                ])

            content_vertical.append(vline_box)

        left = urwid.Pile(content_left)
        right = urwid.Pile(content_right)
        vertical_line = urwid.Pile(content_vertical)

        return urwid.Columns(
            [('fixed', 1, vertical_line), ('fixed', self.ARRAY_WIDTH, left), ('fixed', 1, vertical_line),
             ('fixed', self.ARRAY_WIDTH, right), ('fixed', 1, vertical_line)])

    @staticmethod
    def to_microseconds(in_seconds):
        if not in_seconds:
            return 0
        return round((1000 * in_seconds), MainView.DIGITS)

    def display_stats(self, timeframe):
        """Display the stats calculated from the previous checks for each website

        Used by the alarm in the controller
        """

        body = self.stats_w.body  # .contents
        label = urwid.AttrMap(SelectableText("At time: " + strftime(date_format)), "stats_date",
                              focus_map="stats_date_f")

        stats = [
            urwid.Columns([urwid.Text("For the past " + str(timeframe) + " min: ")])]

        for monitor in self.monitors:
            if monitor.website.display:
                data = monitor.get_stats(timeframe)
                website_stats = urwid.LineBox(
                    urwid.Columns([
                        ('weight', 2, urwid.AttrMap(SelectableText(monitor.website.url), "url", "url_f")),
                        ('weight', 2, urwid.Pile([
                            urwid.Text("Response time max: " + str(self.to_microseconds(data["max_rt"])) + " ms"),
                            urwid.Text("Response time avg: " + str(self.to_microseconds(data["avg_rt"])) + " ms"),
                            urwid.Text("Content loaded in max: " + str(self.to_microseconds(data["max_full_rt"])) + " ms"),
                            urwid.Text("Content loaded in avg: " + str(self.to_microseconds(data["avg_full_rt"])) + " ms"),
                            urwid.Text("Availability: " + str(data["availability"]) + "%"),
                        ])),
                        ('fixed', self.ARRAY_WIDTH*3, self.array_status_codes(data["codes_count"])),
                    ], dividechars=2)
                )

                stats.append(website_stats)

        table = urwid.Pile(stats)

        # Check if the user is currently going through the different stats
        # If it is the case, it does not switch the focus to the new widget
        set_focus = True
        if len(body) > 0 and self.stats_w.focus_position > 0:
            set_focus = False

        # body.insert(0, urwid.Pile([label, table]))
        # If we don't separate label and table the focus will be on the same element:
        # in the stats window, if the user goes through the websites of the last stats, and does not go to
        # previous stats, when the next stats arrives the focus will shift to the new stats (while we want to don't
        # change the focus if the user is going through previous info/stats)
        body.insert(0, table)
        body.insert(0, label)

        if set_focus:
            self.stats_w.set_focus(0, "below")

    def update_monitors(self, monitors):
        """Set the monitors (WebsiteMonitor instances) and transfer them to the DisplaySettings instance"""
        self.monitors = monitors
        self.display_settings.update_monitors(monitors)

    def main_window(self):
        """Set up and return the widget/frame that will be displayed as the main window"""

        history_window = self.history_window()
        stats_window = self.stats_window()
        menu_window = self.menu_window()

        # Columns: arranged horizontally in columns from left to right
        # 1st arg: widget_list containing (flow or box) widgets or tuples. The tuples can be:
        # - ('weight', weight, widget): give this column a relative weight (number) to calculate
        # its width from the screen columns remaining
        # - ('fixed', nb_columns, widget): give this column a width of nb_columns of unit column
        right_window = urwid.Pile(
            [('weight', 4, history_window), ('fixed', 1, hline), ('weight', 3, menu_window)])
        w = urwid.Columns([('weight', 4, stats_window),
                           ('fixed', 2, vline), ('weight', 3, right_window)],
                          dividechars=1, focus_column=2)
        w = urwid.Padding(w, ('fixed left', 1), ('fixed right', 0))
        w = urwid.AttrWrap(w, 'body')
        w = urwid.LineBox(w)
        w = urwid.AttrWrap(w, 'line')

        # A navbar
        header = urwid.AttrMap(urwid.Columns([
            urwid.Text(
                "Website Monitor v1.0. Movements: UP, DOWN, LEFT, RIGHT arrows | Action: spacebar or click | " +
                "To quit: press q"),
        ]), 'header')

        # A frame is a box widget with optional header and footer
        frame = urwid.Frame(w, header=header)
        return frame


class TerminalController:
    """A class responsible for setting up the views and running the application."""

    DISPLAY_INTERVAL = 10  # in seconds
    DISPLAY_LONG_INTERVAL = DISPLAY_INTERVAL * 6  # in seconds
    TIMEFRAME = 10  # in min
    LONG_TIMEFRAME = TIMEFRAME * 6  # in min

    def __init__(self):
        self.loop = None
        self.monitors = None
        self.nb_websites = 0
        self.display_alarm = None

        self.view = MainView(self, self.monitors)

    def main(self):
        # pop_ups=True: wrap widget with a PopUpTarget instance to allow any widget
        # to open a pop-up anywhere on the screen
        self.loop = urwid.MainLoop(self.view, self.view.palette, pop_ups=True, unhandled_input=self.handle_input)

        urwid.connect_signal(self.view, 'exit_settings', lambda element: self.start_monitoring())

        self.loop.run()

        # Will print the message when the program exited by stopping the main loop (the normal exit)
        print("Goodbye !")

    def setup_monitors(self):

        # Check and stop if the monitor is already running
        if self.monitors:
            for monitor in self.monitors:
                monitor.stop()

        # Get the websites from the db
        self.monitors = []
        websites_query = Website.select()
        if websites_query.exists():
            self.nb_websites = websites_query.count()
            for website in websites_query:
                self.monitors.append(WebsiteMonitor(website, self))

        # Transfer the monitors to the MainView instance
        self.view.update_monitors(self.monitors)

    def start_monitoring(self):

        # Init a monitor for each website
        self.setup_monitors()

        # Start the repeated checks
        for monitor in self.monitors:
            monitor.run()

        self.schedule_display()

    def update_alert_history(self):
        """Trigger the update_alert_history from the MainView instance"""
        self.view.update_alert_history()

    def schedule_display(self):
        """Display new stats every every DISPLAY_INTERVAL seconds
        For the scheduler we use the alarm system of urwid

        """
        # Check if a display alarm is already running
        if self.display_alarm:
            self.loop.remove_alarm(self.display_alarm)

        # Start the scheduler/alarm
        self.display_alarm = self.loop.set_alarm_in(self.DISPLAY_INTERVAL, self.loop_display,
                                                    user_data={"chronometer": self.DISPLAY_INTERVAL})

    def loop_display(self, loop=None, user_data=None):
        """Alarm loops to display the stats every DISPLAY_INTERVAL"""
        chronometer = user_data["chronometer"]
        timeframe = self.TIMEFRAME
        if chronometer >= self.DISPLAY_LONG_INTERVAL:
            timeframe = self.LONG_TIMEFRAME
            chronometer = 0

        self.view.display_stats(timeframe)
        self.display_alarm = self.loop.set_alarm_in(self.DISPLAY_INTERVAL, self.loop_display,
                                                    user_data={"chronometer": chronometer + self.DISPLAY_INTERVAL})

    def handle_input(self, key):
        if key in ('q', 'Q'):
            self.exit_program()
        elif key in ('s', 'S'):
            self.view.pop_up_settings.open_pop_up()

    def exit_program(self):
        # Shut down the threads/schedulers before exiting
        if self.monitors:
            for monitor in self.monitors:
                monitor.stop()

        self.loop.remove_alarm(self.display_alarm)

        # And then quit the urwid main loop
        raise urwid.ExitMainLoop()
