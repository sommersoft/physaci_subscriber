# The MIT License (MIT)
#
# Copyright (c) 2020 Michael Schroeder
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
import logging.config
import pathlib
import pkg_resources
import re

from configparser import ConfigParser

from .logger import debug_logger, physaci_logger

_ALT_ALLOWED_SECTIONS = ['physaci', 'node_server']
_STATIC_CONFIG_FILE = pathlib.Path('/etc/opt/physaci_sub/conf.ini')

class PhysaCIConfig():
    """ Container class for holding local configuration results.
    """
    def __init__(self):
        self.alt_config = None
        self.config = ConfigParser(allow_no_value=True, default_section='local')
        read_config = self.config.read(_STATIC_CONFIG_FILE)
        if not read_config:
            physaci_logger.warning('Could not read physaci_subscriber configuration')
            return

        self.config_location = self.config.get('local', 'config_file',
                                               fallback=_STATIC_CONFIG_FILE)
        if self.config_location != _STATIC_CONFIG_FILE.resolve():
            alt_conf_file = pathlib.Path(self.config_location)
            self.alt_config = ConfigParser(allow_no_value=True)
            self.alt_config.read(alt_conf_file)
            read_config = self.config.read([_STATIC_CONFIG_FILE, alt_conf_file],
                                           default_section='local')
            if alt_conf_file not in read_config:
                physaci_logger.warning('Could not read physaci_subscriber alternate configuration')

    @property
    def listen_port(self):
        return self.config.get('node_server', 'listen_port')

    @property
    def physaci_registrar_url(self):
        return self.config.get('local', 'physaci_registrar_url')

    @property
    def physaci_api_key(self):
        return self.config.get('physaci','api_access_key')

    @property
    def node_sig_key(self):
        return self.config.get('node_server','node_sig_key')

    @node_sig_key.setter
    def node_sig_key(self, key):
        self.config['node_server']['node_sig_key'] = key

    def write_config(self):
        """ Write the config file(s) based on key locations, while
            preserving comments. The only field that will be updated
            is the 'node_sig_key' field., depending on where the config
            key is set (static or alternate).
        """
        orig_contents = []
        key_in_alt = bool(
            self.alt_config and
            self.alt_config.get('node_server', 'node_sig_key', None)
        )

        if key_in_alt:
                with open(self.config_location) as read_file:
                    orig_contents = read_file.readlines()
        else:
            with open(_STATIC_CONFIG_FILE) as read_file:
                orig_contents = read_file.readlines()

        new_contents = []
        for line in orig_contents:
            new_contents.append(
                re.sub(r'^node_sig_key\=(.*)$',
                       r'node_sig_key={}'.format(self.node_sig_key),
                       line)
            )

        if key_in_alt:
            with open(self.config_location, 'w') as write_file:
                write_file.writelines(new_contents)
        else:
            with open(_STATIC_CONFIG_FILE, 'w') as write_file:
                write_file.writelines(new_contents)
