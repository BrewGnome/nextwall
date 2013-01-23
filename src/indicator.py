#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of NextWall - A wallpaper changer with some sense of time.
#
#  Copyright 2004, Davyd Madeley <davyd@madeley.id.au>
#  Copyright 2010, 2011, Serrano Pereira <serrano.pereira@gmail.com>
#
#  NextWall is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  NextWall is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import logging
import threading
import hashlib
import urllib
from PIL import Image

import gobject
import pygtk
pygtk.require('2.0')
import gtk
import appindicator

__author__ = "Serrano Pereira"
__copyright__ = ("Copyright 2004, Davyd Madeley\n"
    "Copyright 2010, 2011, Serrano Pereira")
__credits__ = ["Serrano Pereira <serrano.pereira@gmail.com>"]
__license__ = "GPL3"
__version__ = "0.2.2"
__maintainer__ = "Serrano Pereira"
__email__ = "serrano.pereira@gmail.com"
__status__ = "Production"
__date__ = "2011/08/27"


def module_path():
    return os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))

def get_thumbnail_path(filename, dimension='normal'):
    """Given the filename for an image, return the path to the thumbnail file.

    Returns None if there is no thumbnail file.

    Follows the freedesktop.org standards:
    http://people.freedesktop.org/~vuntz/thumbnail-spec-cache/
    """
    # Make sure that the dimension is either 'normal' or 'large'.
    if dimension not in ('normal','large'):
        raise ValueError("Invalid value for thumbnail dimension. Must be either 'normal' or 'large'.")

    # Escape special characters in the path. As stated in the URI RFC 2396
    # standard, unreserved characters (-_.!~*'()) are allowed in the URI and
    # thus should not be escaped here.
    # URI RFC 2396 standard: http://community.roxen.com/developers/idocs/rfc/rfc2396.html
    filename = urllib.quote(filename, safe="/-_.!~*'()")

    # Generate MD5 hash from the absolute canonical URI for the original file.
    file_hash = hashlib.md5('file://'+filename).hexdigest()

    # The filename for the thumbnail is '.png' appended to the hash string.
    tb_filename1 = os.path.join(os.path.expanduser('~/.cache/thumbnails/'+dimension), file_hash) + '.png'
    tb_filename2 = os.path.join(os.path.expanduser('~/.thumbnails/'+dimension), file_hash) + '.png'

    # Return the path to the thumbnail is it exists.
    if os.path.exists(tb_filename1):
        return tb_filename1
    elif os.path.exists(tb_filename2):
        return tb_filename2
    else:
        return None

class Indicator(object):
    """Display an Application Indicator in the GNOME panel."""

    def __init__(self, nextwall):
        self.nextwall = nextwall

        # Create an Application Indicator icon
        ind = appindicator.Indicator("nextwall",
            "nextwall", # Icon name
            appindicator.CATEGORY_OTHER)
        ind.set_status(appindicator.STATUS_ACTIVE)

        # Create GTK menu
        menu = gtk.Menu()

        # Create the menu items
        change_item = gtk.MenuItem("Next Wallpaper")
        info_item = gtk.MenuItem("Image Information")
        open_item = gtk.MenuItem("Open Current")
        show_item = gtk.MenuItem("Show in Browser")
        delete_item = gtk.MenuItem("Delete Current")
        populate_item = gtk.MenuItem("Scan Wallpapers Folder")
        pref_item = gtk.MenuItem("Preferences")
        quit_item = gtk.MenuItem("Quit")
        separator = gtk.SeparatorMenuItem()

        # Add them to the menu
        menu.append(change_item)
        menu.append(info_item)
        menu.append(open_item)
        menu.append(show_item)
        menu.append(delete_item)
        menu.append(populate_item)
        menu.append(separator)
        menu.append(pref_item)
        menu.append(quit_item)

        # Attach the callback functions to the activate signal
        change_item.connect("activate", self.on_change_background)
        info_item.connect("activate", self.on_image_info)
        open_item.connect("activate", self.on_open_current)
        show_item.connect("activate", self.on_show_file)
        delete_item.connect("activate", self.on_delete_current)
        populate_item.connect("activate", self.on_scan_for_images)
        pref_item.connect("activate", self.on_preferences)
        quit_item.connect("activate", self.on_quit)

        # Show menu items
        menu.show_all()

        # Add the menu to the Application Indicator
        ind.set_menu(menu)

        # Create Image Information dialog.
        self.image_info = ImageInformation(self.nextwall)

        # Run the main loop
        gtk.main()

    def on_change_background(self, widget=None, data=None):
        return_code = self.nextwall.change_background()
        if return_code == 1:
            message = ("No wallpapers found")
            dialog = gtk.MessageDialog(parent=None, flags=0,
                type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO,
                message_format=message)
            dialog.format_secondary_text("No image files are known for the selected "
                "wallpapers folder. If the \"fit time of day\" feature is enabled, "
                "there might not be a wallpaper for the current time of day. "
                "Would you like to scan the folder for more images?")
            response = dialog.run()
            dialog.destroy()

            if response == gtk.RESPONSE_YES:
                self.on_scan_for_images()
        elif return_code == 2:
            message = ("Not enough wallpapers")
            dialog = gtk.MessageDialog(parent=None, flags=0,
                type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO,
                message_format=message)
            dialog.format_secondary_text("Not enough image files are known for the selected "
                "wallpapers folder. If the \"fit time of day\" feature is enabled, "
                "there might not be a wallpaper for the current time of day. "
                "Would you like to scan the folder for more images?")
            response = dialog.run()
            dialog.destroy()

            if response == gtk.RESPONSE_YES:
                self.on_scan_for_images()
        else:
            # Update image info dialog.
            self.image_info.update()

    def on_image_info(self, widget, data=None):
        """Display image information."""
        self.image_info.update()
        self.image_info.show()

    def on_quit(self, widget, data=None):
        """Exit the application."""
        gtk.main_quit()

    def on_preferences(self, widget, data=None):
        """Display preferences window."""
        Preferences(self.nextwall)

    def on_delete_current(self, widget, data=None):
        """Delete the current background image from the harddisk."""
        current_bg = self.nextwall.get_background_uri()
        message = ("This will <b>permanently</b> remove the current background "
            "image (%s) from your harddisk.") % (current_bg)

        dialog = gtk.MessageDialog(parent=None, flags=0,
            type=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_YES_NO,
            message_format=None)
        dialog.set_markup(message)
        dialog.format_secondary_text("Continue?")
        response = dialog.run()

        if response == gtk.RESPONSE_YES:
            logging.info("Removing %s" % (current_bg))
            os.remove(current_bg)
            dialog.destroy()
        else:
            dialog.destroy()
            return

        # Change the background.
        self.on_change_background()

    def on_open_current(self, widget, data=None):
        """Open the current background with the system's default image
        viewer.
        """
        current_bg = self.nextwall.get_background_uri()
        os.system('xdg-open "%s"' % (current_bg))

    def on_show_file(self, widget, data=None):
        """Show the file in the default file browser."""
        current_bg = self.nextwall.get_background_uri()
        os.system('nautilus --no-desktop "%s"' % (current_bg))

    def on_scan_for_images(self, widget=None, data=None):
        """Run the main._scan_for_images function in a separate thread, and
        show a nice progress dialog.
        """
        # Display the load backgrounds dialog.
        pgd = ScanWallpapersDialog(self.nextwall)

        # Start the PopulateDB class in a new thread.
        pdb = PopulateDB(pgd)
        pdb.start()

class ImageInformation(object):
    """Display a dialog showing the image information."""

    def __init__(self, nextwall):
        self.nextwall = nextwall

        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(module_path(), 'glade/image_info.glade'))

        # Get some GTK objects.
        self.dialog = self.builder.get_object('image_info_dialog')
        self.thumbnail = self.builder.get_object('image_thumb')
        self.label_path_value = self.builder.get_object('label_path_value')
        self.label_kurtosis_value = self.builder.get_object('label_kurtosis_value')
        self.label_size_value = self.builder.get_object('label_size_value')
        self.combobox_brightness = self.builder.get_object('combobox_brightness')

        # Connect the window signals to the handlers.
        self.builder.connect_signals(self)
        self.dialog.connect('delete-event', self.hide)

        # Add items to the "New brightness" combobox.
        #print gobject.type_name(gobject.TYPE_STRING)
        cell = gtk.CellRendererText()
        self.combobox_brightness.pack_start(cell, True)
        self.combobox_brightness.add_attribute(cell, 'text', 0)
        self.combobox_brightness.append_text('Night')
        self.combobox_brightness.append_text('Twilight')
        self.combobox_brightness.append_text('Day')

        # Hide the dialog.
        self.hide()

    def show(self, widget=None, data=None):
        """Show the dialog."""
        self.dialog.show_all()

    def hide(self, widget=None, data=None):
        """Hide the dialog."""
        self.dialog.hide()
        # Prevent default action.
        return True

    def update(self):
        # Get the current background.
        self.current_bg = self.nextwall.get_background_uri()

        # Get the image brightness for the current background.
        kurtosis, self.brightness = self.nextwall.get_image_brightness(self.current_bg, get=True)

        # Get the path to the thumbnail of the current background.
        thumb_path = get_thumbnail_path(self.current_bg, 'normal')

        # Show the thumbnail.
        if thumb_path:
            self.thumbnail.set_from_file(thumb_path)
        else:
            self.thumbnail.set_from_stock(gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_DIALOG)

        # Get the image's width and height in pixels.
        img = Image.open(self.current_bg)
        image_size = "%d x %d pixels" % img.size

        # Update the values for the labels.
        self.label_path_value.set_text(self.current_bg)
        self.label_kurtosis_value.set_text(str(kurtosis))
        self.label_size_value.set_text(image_size)

        # Set brightness.
        self.combobox_brightness.set_active(self.brightness)

    def on_button_ok_clicked(self, widget, data=None):
        """Save settings and close the dialog."""
        # Get the selected brightness value.
        active = self.combobox_brightness.get_active()

        # Set the new brightness value.
        self.nextwall.set_defined_brightness(self.current_bg, active)

        # Hide the dialog.
        self.dialog.hide()

class Preferences(object):
    """Display a preferences dialog which allows the user to configure
    the application.
    """

    def __init__(self, nextwall):
        self.nextwall = nextwall

        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(module_path(), 'glade/preferences.glade'))

        # Connect the window signals to the handlers.
        self.builder.connect_signals(self)

        # Get some GTK objects.
        self.dialog = self.builder.get_object('preferences_dialog')
        self.chooser_backgrounds_folder = self.builder.get_object('chooser_backgrounds_folder')
        self.checkbutton_recursion = self.builder.get_object('checkbutton_recursion')
        self.checkbutton_fit_time = self.builder.get_object('checkbutton_fit_time')
        self.entry_lat = self.builder.get_object('entry_lat')
        self.entry_lon = self.builder.get_object('entry_lon')

        # Transform the layout.
        self.transform_layout()

    def transform_layout(self):
        # Set the path for the folder chooser.
        self.chooser_backgrounds_folder.set_current_folder(self.nextwall.path)

        # Enable/disable recusion checkbutton.
        if self.nextwall.recursive:
            self.checkbutton_recursion.set_active(True)

        # Enable/disable fit time checkbutton.
        if self.nextwall.fit_time:
            self.checkbutton_fit_time.set_active(True)

        # Set latitude and longitude values.
        self.entry_lat.set_text(str(self.nextwall.latitude))
        self.entry_lon.set_text(str(self.nextwall.longitude))

    def on_button_ok_clicked(self, widget, data=None):
        """Save new settings and close the preferences dialog."""
        # Set the new backgrounds folder.
        self.nextwall.set_backgrounds_folder( self.chooser_backgrounds_folder.get_filename() )

        # Set recursion.
        if self.checkbutton_recursion.get_active():
            self.nextwall.recursive = True
        else:
            self.nextwall.recursive = False

        # Set match time.
        if self.checkbutton_fit_time.get_active():
            self.nextwall.set_fit_time(True)
        else:
            self.nextwall.set_fit_time(False)

        # Set latitude and longitude values.
        lat_lon_set = False
        latitude = self.entry_lat.get_text()
        longitude = self.entry_lon.get_text()

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            dialog = gtk.MessageDialog(parent=None, flags=0,
                type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK,
                message_format="Latitude and longitude")
            dialog.format_secondary_text("The values you entered for latitude "
                "and longitude are not correct. Please correct the values.")
            dialog.set_position(gtk.WIN_POS_CENTER)
            dialog.run()
            dialog.destroy()
            return

        error = self.nextwall.set_lat_lon(latitude, longitude)
        lat_lon_set = True

        # Make sure that both latitude and longitude are set if the fit time
        # of day checkbox is checked.
        if self.checkbutton_fit_time.get_active() and not lat_lon_set:
            dialog = gtk.MessageDialog(parent=None, flags=0,
                type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK,
                message_format="Latitude and longitude")
            dialog.format_secondary_text("Latitude and longitude must be set "
                "for the fit time of day feature to work. Please set these values.")
            dialog.set_position(gtk.WIN_POS_CENTER)
            dialog.run()
            dialog.destroy()
            return

        # Destroy the dialog.
        self.dialog.destroy()

    def on_button_cancel_clicked(self, widget, data=None):
        """Close the preferences dialog."""
        self.dialog.destroy()

    def on_button_about_clicked(self, widget, data=None):
        About()

class About(object):
    def __init__(self):
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(module_path(), 'glade/about.glade'))

        about = builder.get_object('about_dialog')
        about.set_logo_icon_name("nextwall")
        about.set_version(__version__)
        about.set_copyright(__copyright__)
        about.set_authors(__credits__)
        about.run()
        about.destroy()

class ScanWallpapersDialog(object):
    """Show the load backgrounds dialog."""

    def __init__(self, nextwall):
        self.nextwall = nextwall
        self.nextwall.scan_for_images = True

        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(module_path(), 'glade/scan_backgrounds.glade'))

        # Connect the window signals to the handlers.
        self.builder.connect_signals(self)

        # Get some GTK objects.
        self.dialog = self.builder.get_object('scan_backgrounds_dialog')

    def on_destroy(self, widget=None, data=None):
        self.nextwall.scan_for_images = False
        self.dialog.destroy()

class PopulateDB(threading.Thread):
    """Analyze all image files in the specified folder and update the
    progress bar in the progress dialog. The result is that all the
    information will be saved to the database file.
    """

    def __init__(self, parent):
        super(PopulateDB, self).__init__()
        self.parent = parent
        self.current = 0
        self.total = 0
        self.progress_bar = self.parent.builder.get_object('progressbar')

    def update_progressbar(self):
        fraction = self.current / float(self.total)

        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text("%d/%d" % (self.current, self.total))

        if self.current == self.total:
            self.progress_bar.set_text("Finished!")

        return False

    def run(self):
        """Calculate the image kurtosis for each image in the selected
        folder and save it to the database.
        """
        images = self.parent.nextwall.get_image_files()
        self.total = len(images)

        if self.total == 0:
            gobject.idle_add(self.progress_bar.set_text, "No image files found")
            return False

        # Get the image kurtosis of each file and save it to the
        # database.
        for i, image in enumerate(images, start=1):
            if not self.parent.nextwall.scan_for_images:
                # Stop the process if 'scan_for_images' set to False.
                logging.info("Analyze images: stopped by user.")
                return False

            self.current = i
            logging.info("Found %s" % (image))
            gobject.idle_add(self.update_progressbar)
            self.parent.nextwall.get_image_kurtosis(image)

        logging.info("Image files successfully scanned.")
