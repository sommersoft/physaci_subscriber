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

import hmac
import logging
import logging.config
import json
import pkg_resources
import pathlib
import secrets

from base64 import b64encode
from hashlib import sha256
from datetime import datetime, timezone
from socket import gethostname

import requests

from physaci_subscriber.config import PhysaCIConfig

from .logger import debug_logger, physaci_logger

class PhysaCISubscribe():
    """ Class to handle generating and sending subscription notices
        to physaCI.
    """
    def __init__(self):
        self.configuration = PhysaCIConfig()
        debug_logger.debug('PhysaCISubscribe config: {}'.format(list(self.configuration.config.items())))

    def generate_node_key(self):
        """ Generate a new URL-safe key to be used with HTTP signatures
            from physaCI push messages.
        """

        old_key = self.configuration.node_sig_key
        new_key = secrets.token_urlsafe(64)

        if secrets.compare_digest(old_key, new_key):
            self.cofiguration.node_sig_key = ""
            self.configuration.write_config()
            conf_loc = self.configuration.config_location
            message = (
                "Could not generate acceptable key. "
                "'{}' updated with null key value.".format(config_loc)
            )
            physaci_logger.error(message)
            raise RuntimeError(message)

        self.configuration.node_sig_key = new_key

    def node_busy_status(self):
        """ Check if the current node is busy, using the node_server API.
        """
        if not self.configuration.node_sig_key:
            return {'busy': False}

        busy_status = {}

        header = {
            'Host': '127.0.0.1',
            'Date': datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:S GMT'),
        }

        sig_string = "{}\n{}".format(header['Host'], header['Date'])
        sig_hashed = hmac.new(
            self.configuration.node_sig_key.encode(),
            msg=sig_string.encode(),
            digestmod=sha256
        )
        signature = [
            'Signature ',
            'keyID="{}",'.format(gethostname()),
            'algorithm="hmac-sha256",',
            'headers="{}",'.format([hdr.lower() for hdr in header.keys()]),
            'signature={}'.format(b64encode(sig_hashed.digest()))
        ]
        header['Authorization'] = ''.join(signature)

        url = 'http://127.0.0.1:{}/status'.format(self.configuration.listen_port)

        try:
            response = requests.get(url, headers=header)
            if response.ok:
                busy_status = response.json()
        except requests.exceptions.ConnectionError:
            physaci_logger.warning(
                'Could not determine node busy status. Connection to node '
                'server failed.'
            )
            pass

        return busy_status

    def send_subscription(self):
        """ Send a new subscription notification to physaCI. Will include
            a new node signature key for use with an HTTP Signature header
            inside pushed notifications.
        """
        physaci_logger.info('Initiating physaCI registrar subscription.')
        sub_message = {
            'node_name': gethostname(),
            'listen_port': self.configuration.listen_port,
            'busy': self.node_busy_status().get('busy', False)
        }

        debug_logger.info('Generating new node signature key.')
        self.generate_node_key()
        sub_message['node_sig_key'] = self.configuration.node_sig_key

        url = self.configuration.physaci_registrar_url
        header = {'x-functions-key': self.configuration.physaci_api_key}

        debug_logger.info('Sending subscription request.')
        response = requests.post(url, headers=header, json=sub_message)
        if response.ok:
            self.configuration.write_config()
            physaci_logger.info("Successfully subscribed.")
        else:
            log_message = [
                'Subscription request failed',
                'Response status code: {}'.format(response.status_code),
                'Response Message: {}'.format(response.text),
            ]
            physaci_logger.error(' | '.join(log_message))


def subscribe_to_registrar():
    subscriber = PhysaCISubscribe()
    subscriber.send_subscription()
