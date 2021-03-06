# -*- coding: utf-8 -*-
# Copyright (C) Cardiff University (2019-2020)
#
# This file is part of ciecplib.
#
# ciecplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ciecplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ciecplib.  If not, see <http://www.gnu.org/licenses/>.

"""User-interface functions for SAML ECP authentication
"""

import math
import string
from urllib import parse as urllib_parse

from OpenSSL import crypto

from .env import DEFAULT_IDP
from .cookies import extract_session_cookie
from .requests import _ecp_session
from .utils import (
    DEFAULT_SP_URL,
    random_string,
)

__author__ = "Duncan Macleod <duncan.macleod@ligo.org>"


@_ecp_session
def get_cookie(
        url,
        endpoint=DEFAULT_IDP,
        hours=168,
        username=None,
        kerberos=False,
        spurl=DEFAULT_SP_URL,
        debug=False,
        session=None,
):
    # decorator guarantees a populated session
    with session as sess:
        # authenticate against the endpoint
        sess.ecp_authenticate(
            url=url,
        )

        # extract the shibsession cookie for the SP:
        #   we do this by searching for all cookies associated with
        #   the relevant SP domain, and picking the most recent one
        return extract_session_cookie(sess.cookies, url)


@_ecp_session
def get_cert(
        endpoint=DEFAULT_IDP,
        hours=168,
        username=None,
        kerberos=False,
        spurl=DEFAULT_SP_URL,
        debug=False,
        session=None,
):
    # decorator guarantees a populated session
    with session as sess:
        cookie = get_cookie(spurl, session=sess, debug=debug)

        if debug:
            print("Authenticated against IdP with ECP")
            print("Requesting certificate from {0}".format(spurl))

        # request PKCS12 certificate from SP
        csrfstr = random_string(10)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': 'CSRF={0}; {1.name}={1.value}'.format(csrfstr, cookie),
        }
        p12password = (
            random_string(16, string.ascii_letters) +
            random_string(2, string.digits) +
            random_string(2, '!@#$%^&*()')
        )
        certdata = urllib_parse.urlencode({
            'submit': 'pkcs12',
            'CSRF': csrfstr,
            'p12password': p12password,
            'p12lifetime': math.ceil(hours),
        }).encode('utf-8')
        resp = sess.post(
            spurl,
            data=certdata,
            headers=headers,
        )

        if debug:
            print("Certificate received.")
        return crypto.load_pkcs12(
            resp.content,
            p12password.encode('utf-8'),
        )
