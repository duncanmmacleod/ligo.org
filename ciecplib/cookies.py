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

"""Cookie handling for SAML ECP authentication
"""

import time
from http.cookiejar import (LoadError, MozillaCookieJar)
from urllib.parse import urlparse

from requests.cookies import RequestsCookieJar

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'


# -- cookie jar ---------------------------------------------------------------

class ECPCookieJar(RequestsCookieJar, MozillaCookieJar):
    """Custom cookie jar

    Adapted from
    https://wiki.shibboleth.net/confluence/download/attachments/4358416/ecp.py
    """
    def save(self, filename=None, ignore_discard=False, ignore_expires=False):
        with open(str(filename), 'w') as f:
            f.write(self.header)
            for cookie in self:
                if not ignore_discard and cookie.discard:
                    continue
                if not ignore_expires and cookie.is_expired(time.time()):
                    continue
                if cookie.expires is not None:
                    expires = str(cookie.expires)
                else:
                    # change so that if a cookie does not have an expiration
                    # date set it is saved with a '0' in that field instead
                    # of a blank space so that the curl libraries can
                    # read in and use the cookie
                    expires = "0"
                if cookie.value is None:
                    # cookies.txt regards 'Set-Cookie: foo' as a cookie
                    # with no name, whereas cookiejar regards it as a
                    # cookie with no value.
                    name = ""
                    value = cookie.name
                else:
                    name = cookie.name
                    value = cookie.value
                print('\t'.join([
                    cookie.domain,
                    str(cookie.domain.startswith('.')).upper(),
                    cookie.path,
                    str(cookie.secure).upper(),
                    expires,
                    name,
                    value,
                ]), file=f)

    def _really_load(self, f, filename, ignore_discard, ignore_expires):
        out = super(ECPCookieJar, self)._really_load(
            f,
            filename,
            ignore_discard,
            ignore_expires,
        )
        for cookie in self:
            if not cookie.expires:
                cookie.expires = None
        return out


# -- utilities ----------------------------------------------------------------

def extract_session_cookie(jar, url):
    """Returns s session cookie for the given URL from the jar

    Parameters
    ----------
    jar : `http.cookiejar.CookieJar`
        the cookie jar to check

    url : `str`
        the URL of the service that needs cookies

    Returns
    -------
    cookie : `http.cookielib.Cookie`
        the relevant cookie

    Raises
    ------
    ValueError
        if no appropriate cookie is found
    """
    url = urlparse(url).netloc
    for cookie in list(jar)[::-1]:
        if (
                cookie.name.startswith("_shibsession_") and
                cookie.domain == url and
                cookie.expires is None
        ):
            return cookie
    raise ValueError(
        "no shibsession cookie found for {!r}".format(url),
    )


def has_session_cookies(jar, url):
    """Returns `True` if the given cookie jar has a session cookie we can use

    Parameters
    ----------
    jar : `http.cookiejar.CookieJar`
        the cookie jar to check

    url : `str`
        the URL of the service that needs cookies

    Returns
    -------
    can_reuse : `bool`
        `True` if any cookie in the jar is a non-expiring ``shibsession``
        cookie for the given same domain as ``url``
    """
    try:
        extract_session_cookie(jar, url)
    except ValueError:
        return False
    return True


def load_cookiejar(
        cookiefile,
        strict=True,
        ignore_discard=True,
        ignore_expires=True,
):
    """Load a cookie jar from a file

    Parameters
    ----------
    cookiefile : `str`
        path to cookie jar file

    strict : `bool`, optional
        if `True` (default), raise all exceptions as they occur,
        if `False` just emit warnings

    ignore_discard, ignore_expires : `bool`, optional
        options to pass to :meth:`ECPCookieJar.load`, both default to
        `True` in this usage.
    """
    cookiejar = ECPCookieJar()
    try:
        cookiejar.load(
            str(cookiefile),
            ignore_discard=ignore_discard,
            ignore_expires=ignore_expires,
        )
    except (LoadError, OSError):
        if strict:
            raise
    return cookiejar
