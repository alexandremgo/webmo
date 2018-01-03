import urwid
from urllib.parse import urlparse

from .models import Website
from .website_monitor import WebsiteMonitor

# A blank line
blank = urwid.Divider()


class WebsiteForm(urwid.WidgetWrap):
    """A form to register and edit information for a website. The form handles itself the submit process"""

    def __init__(self, cur_website):
        """cur_website = a Website model. It can be empty (insert) or full (update)"""
        self.website = cur_website
        # TODO: tej ça
        # close_button = urwid.Button("Exit")
        # urwid.connect_signal(close_button, 'click',
        #                      lambda button: self._emit("close"))

        description = ("Form for the website: " + self.website.url) if self.website.id else "Form for a new website"

        # Confirmation message shown when the website has been saved
        self.confirmation = urwid.Text("")
        # The inputs of the form:
        self.input_website = urwid.Edit("Your website url: ", self.website.url)
        self.input_check_interval = urwid.IntEdit("Check interval (in seconds): ", self.website.check_interval)
        # Put vertically the different inputs and labels
        pile = urwid.Pile([
            urwid.Text(description),
            blank,
            urwid.AttrMap(self.input_website, 'input', 'input_f'),
            blank,
            urwid.AttrMap(self.input_check_interval, 'input', 'input_f'),
            blank,
            urwid.AttrMap(urwid.Padding(
                urwid.Button("Submit", self.submit_press),
                width=10), 'button', 'button_f'),
            blank,
            urwid.AttrMap(self.confirmation, 'submit_confirmation'),
            blank
        ])
        fill = urwid.Filler(pile)
        self.__super.__init__(urwid.AttrMap(fill, 'body'))

    def submit_press(self, button):
        # Check the url:
        url = self.input_website.get_edit_text()
        check_interval = self.input_check_interval.value()
        if not url:
            self.confirmation.set_text("The website url cannot be empty")
        elif check_interval < 1:
            self.confirmation.set_text("The check interval must be greater than or equal to 1 second")
        else:
            parsed_url = urlparse(url)
            # If an http or https is given it will keep it. Otherwise http
            scheme = parsed_url.scheme if parsed_url.scheme in WebsiteMonitor.CORRECT_SCHEMES else "http"
            # netloc: the domain name of the url if there was a scheme before
            # path: the path just after the domain name or the domain name if there was no scheme
            url = scheme + "://" + parsed_url.netloc + parsed_url.path

            # Then save the website in the db
            self.website.url = url
            self.website.check_interval = check_interval
            self.confirmation.set_text("The website " + self.website.url + " has been saved")
            self.website.save()


class SettingsMenu(urwid.WidgetWrap):
    """The settings window for websites that appears as a pop-up"""

    # Signals that SettingsMenu instances can emit
    signals = ['close', 'reload']

    MAX_URL = 55

    def __init__(self):
        # Get the already registered websites
        websites_query = Website.select()
        menu_structure = [
            urwid.Padding(
                self.menu_button("Add a website", lambda button: self.edit_website(Website())),
                width=17
            ),
            urwid.Text("or")
        ]

        if websites_query.exists():
            nb_websites = websites_query.count()
            for website in websites_query:
                menu_structure.append(
                    self.sub_menu("Website: " + website.url[7:self.MAX_URL], [
                        # Default parameter event_website in order to bind to the reference website is pointing to
                        # because Python looks up the variable name at the time the function is called
                        # TODO: use week_args or user_args ?: http://urwid.org/reference/signals.html?highlight=signal
                        urwid.Padding(
                            self.menu_button("Edit",
                                             lambda button, event_website=website: self.edit_website(event_website)),
                            width=10),
                        urwid.Padding(
                            self.menu_button("Delete",
                                             lambda button, event_website=website: self.delete_website(event_website)),
                            width=10),
                    ])
                )

        menu_structure = self.menu("Settings", menu_structure)

        # What is at the top of the cascading menu
        self.top = self.CascadingBoxes(menu_structure)
        # Forward the close and reload signals to its SettingsPopUp
        urwid.connect_signal(self.top, 'close', lambda button: self._emit('close'))
        urwid.connect_signal(self.top, 'reload', lambda button: self._emit('reload'))

        super().__init__(self.top)

    def menu_button(self, caption, callback):
        """The last layer: a button that will trigger an action (the callback)"""
        button = urwid.Button(caption)
        urwid.connect_signal(button, 'click', callback)
        return urwid.AttrMap(button, 'button', focus_map='button_f')

    def sub_menu(self, caption, choices):
        """The intermediary layer for the cascading menu: just forward to another layer"""
        contents = self.menu(caption, choices)

        def open_menu(button):
            return self.top.open_box(contents)

        return self.menu_button(caption, open_menu)

    def menu(self, title, choices):
        """The first layer and also structure for a sub_menu"""
        body = [urwid.Text(title), urwid.Divider()]
        body.extend(choices)
        return urwid.ListBox(urwid.SimpleFocusListWalker(body))

    def edit_website(self, website):
        """Callback function to edit an existing website"""
        self.top.open_box(WebsiteForm(website))

    def delete_website(self, cur_website):
        """Callback function to delete a website from the db"""

        # TODO: a confirmation message before
        cur_website.delete_instance()
        # Go back to the main menu with the websites list updated
        self._emit('reload')

    class CascadingBoxes(urwid.WidgetPlaceholder):
        """Class handling the superposition of different layers of windows (boxes) for the menu"""

        # Signals that CascadindBoxes can emit
        signals = ['close', 'reload']

        # To calculate the margin between boxes/menus
        MAX_BOX_LEVELS = 3
        # Height of the box just above the return and exit buttons
        BOX_HEIGHT = 10

        def __init__(self, box):
            super().__init__(urwid.AttrMap(urwid.SolidFill(u'/'), 'main_shadow'))
            self.first_top = box
            self.box_level = 0
            self.open_box(box)

        def open_box(self, box):
            """Display the current top (window) layer of the menu"""

            return_button = urwid.AttrMap(
                urwid.Button("Return", lambda button: self.go_previous_layer()),
                'button', 'button_f')
            # Send a signal to inform that the user wants to close the menu
            exit_button = urwid.AttrMap(
                urwid.Button("Start monitoring", lambda button: self._emit('close')),
                'button', 'button_f')

            buttons = [blank]
            if self.box_level > 0:
                buttons.append(urwid.Padding(return_button, width=10))
            buttons.append(urwid.Padding(exit_button, width=20))

            buttons = urwid.Pile(buttons)

            focus_item = None
            # On the first box (the main setting view), the exit button is selected so that the user can start to
            # monitor just by clicking on the button
            if self.box_level == 0:
                focus_item = buttons

            box = urwid.Filler(urwid.Pile([urwid.BoxAdapter(box, self.BOX_HEIGHT), buttons], focus_item=focus_item))
            box = urwid.AttrMap(urwid.LineBox(box), 'body')
            self.original_widget = urwid.Overlay(box,
                                                 self.original_widget,
                                                 align='center', width=('relative', 100),
                                                 valign='middle', height=('relative', 105),
                                                 min_width=24, min_height=14,
                                                 left=self.box_level * 3,
                                                 right=(self.MAX_BOX_LEVELS - self.box_level - 1) * 3,
                                                 top=self.box_level * 2,
                                                 bottom=(self.MAX_BOX_LEVELS - self.box_level - 1) * 2)
            self.box_level += 1

        def go_previous_layer(self):
            """Return to the previous layer of the menu's structure"""

            # if self.box_level > 1:
            #     self.original_widget = self.original_widget[0]
            #     self.box_level -= 1

            # Actually we need to reload the information especially when a website has been created or updated
            self._emit("reload")

        def keypress(self, size, key):
            if key == 'esc' and self.box_level > 1:
                self.go_previous_layer()
            else:
                return super().keypress(size, key)


class SettingsPopUp(urwid.PopUpLauncher):
    signals = ['exit_settings']

    def __init__(self, original_widget):
        """The original widget is the widget shown when the pop up is closed
        It is a button widget given to the PopUpLaucher's __init__ function
        """
        self.__super.__init__(original_widget)
        urwid.connect_signal(self.original_widget, 'click',
                             lambda button: self.open_pop_up())

    def create_pop_up(self):
        """Return a widget used for the pop_up/dialog box"""
        pop_up = SettingsMenu()

        # Catch the signal "close" sent by a button exist
        urwid.connect_signal(pop_up, 'close',
                             lambda button: self.close())
        # The same for the signal "reload"
        urwid.connect_signal(pop_up, 'reload',
                             lambda button: self.open_pop_up())

        return pop_up

    def get_pop_up_parameters(self):
        """Parameters of the pop up/dialog box:
        left and top (in number of rows and columns): relative to the original widget (here the button add a website)
        overlay_width and overlay_height: in number of rows and columns
        """
        return {'left': -60, 'top': -20, 'overlay_width': 100, 'overlay_height': 30}

    def close(self):
        self.close_pop_up()
        self._emit('exit_settings')


class DisplaySettings(urwid.WidgetWrap):
    """Check buttons/boxes that enable or disable the display of checks for each website"""

    CELL_WIDTH = 35

    def __init__(self, monitors):
        self.monitors = monitors

        self.grid = urwid.GridFlow([], self.CELL_WIDTH, 3, 1, 'left')
        self.display_settings()  # at init, at there is no monitors, it will display nothing

        self.__super.__init__(urwid.AttrMap(
            urwid.Padding(self.grid, left=0, right=0, min_width=13)
            , 'body')
        )

    def update_monitors(self, monitors):
        """Method called by other element to tell the DisplaySettings instance that the monitors have been modified"""
        self.monitors = monitors
        self.display_settings()

    def display_settings(self):
        """Fill the grid widget with check buttons for each website. Each button is "linked" to the website's monitor"""
        content = []

        if self.monitors:
            for monitor in self.monitors:
                content.append((urwid.AttrWrap(urwid.CheckBox(monitor.website.url[7:self.CELL_WIDTH - 5],
                                                              state=monitor.website.display,
                                                              on_state_change=self.change_display,
                                                              user_data={"monitor": monitor}
                                                              )
                                               , 'check_box', 'check_box_f'),
                                self.grid.options()))

        self.grid.contents = content

    def change_display(self, radio_button, new_state, user_data):
        """Callback function when the user changes the value of a check button"""
        monitor = user_data['monitor']
        monitor.website.display = new_state
        monitor.website.save()
