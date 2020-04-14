"""
Python driver for Brooks Instrument flow controllers.

Distributed under the GNU General Public License v2
Copyright (C) 2020 NuMat Technologies
"""
from urllib.parse import urlencode


import aiohttp

ERROR_CODES = {
  "Alarm0": "Low Flow Alarm",
  "Alarm1": "High Flow Alarm",
  "Alarm2": "No Flow Alarm",
  "Alarm3": "Choked Flow Alarm",
  "Alarm15": "Invalid Calibration Page Select",
  "Alarm23": "Using Backup NV memory",
  "Alarm24": "Temperature Sensor Fail",
  "Warn0": "Low Flow Warning",
  "Warn1": "High Flow Warning",
  "Warn3": "Choked Flow Warning",
  "Warn4": "Excessive Zero Drift Warning",
  "Warn5": "Bad Zero Warning",
  "Warn8": "Valve High Warning",
  "Warn9": "Valve Low Warning",
  "Warn11": "Setpoint Deviation Warning",
  "Warn13": "Setpoint Overrange Warning",
  "Warn14": "Setpoint Limited Warning",
  "Warn17": "Calibration Due Warning",
  "Warn18": "Totalizer Overflow Warning",
  "Warn19": "Overhaul Due Warning",
  "Warn24": "High Temperature Warning",
  "Warn25": "Low Temperature Warning",
  "Warn26": "Supply Volts High Warning",
  "Warn27": "Supply Volts Low Warning"
}

STATUS_CODE = {'Fl': 'Flow', 'SP': 'Setpoint', 'LSP': 'Live Setpoint',
                'VP': 'Valve Position', 'TP': 'Temperature',
                'Tot': 'Flow Totalizer', 'Ctot': 'Customer Flow Totalizer',
                'Hrs': 'Flow Hours', 'OpHrs': 'Operational Hours',
                'Volt': 'Supply Voltage'}


class FlowController(object):
    """Driver for Brooks Instrument mass flow controllers."""

    def __init__(self, address, timeout=10, password='control'):
        """Initialize device.

        Note that this constructor does not not connect. This will happen
        on the first avaiable async call (ie. `await mfc.get()` or
        `async with FlowController(ip) as mfc`).

        Args:
            address: The IP address of the device, as a string.
            timeout (optional): Time to wait for a response before throwing
                a TimeoutError. Default 1s.
            password (optional): Password used to access admin settings on the
                web interface. Default "control".

        """
        self.http_address = f"http://{address.lstrip('http://').rstrip('/')}/"
        self.ws_address = f"ws://{address.lstrip('http://').rstrip('/')}/"
        self.session = None
        self.ws_session = None
        self.web_socket = None
        self.timeout = timeout
        self.password = password
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    async def __aenter__(self):
        """Support `async with` by entering a client session."""
        try:
            await self.connect_ws()
        except Exception as e:
            await self.__aexit__(e)
        return self

    async def __aexit__(self, *err):
        """Support `async with` by exiting a client session."""
        await self.disconnect()

    async def connect_http(self):
        """Connect to server and authenticate

        Configuration and some device information retrieval is done though
        post requests with a valid session cookie. This method refreshes that
        connection.
        """
        self.session = aiohttp.ClientSession(read_timeout=self.timeout)
        await self._request("brooks_login.html",
                            body={'password': 'control', 'access_level': 2},
                            reconnect_on_error=False)

    async def connect_ws(self):
        """Connect to the Web Socket.

        Realtime process information is returned via an unauthenticated
        websocket connection.
        """
        self.ws_session = aiohttp.ClientSession(read_timeout=self.timeout)
        self.web_socket = await self.ws_session.ws_connect(self.ws_address)

    async def disconnect(self):
        """Close the underlying session, if it exists."""
        if self.session is not None:
            await self.session.close()
            self.session = None
        if self.web_socket is not None:
            self.ws_session.close()
            self.web_socket = None

    async def get(self):
        """Retrieve the device state.

        This is done using a websocket interface.
        """
        if not self.web_socket:
            await self.connect_ws()
        await self.web_socket.send_str('A')
        response = await self.web_socket.receive_json()
        return {STATUS_CODE[k]: float(v) for k, v in response.items()
                if k in STATUS_CODE}

    async def set(self, setpoint):
        """Set the setpoint flow rate, in percent.

        This uses an undocumented HTTP extension, `Control.html`.

        Args:
            setpoint: Setpoint flow, as a float, in percent.
        """
        if setpoint < 0 or setpoint > 100:
            raise ValueError(f"Setpoint must be between 0 and 100 percent.")
        await self._request('Control.html', {0: setpoint})

    async def open(self):
        """Set the flow to its maximum value."""
        await self.set(100)

    async def close(self):
        """Set the flow to zero."""
        await self.set(0)

    async def _request(self, endpoint, body=None, reconnect_on_error=True):
        """Handle sending an HTTP request.

        If request fails, it may be caused by a stale session cookie.
        We attempt a reconnect and re-request.
        """
        if self.session is None:
            await self.connect_http()
        url = self.http_address + endpoint
        method = ('POST' if body else 'GET')
        data = urlencode(body)
        self.headers['Content-Length'] = str(len(data))
        async with self.session.request(method, url, data=data,
                                        headers=self.headers) as r:
            # I can't seem to get aiohttp to set cookies in it's client
            # session correctly so I resort to this for now
            if 'Set-Cookie' in r.headers:
                cookie = r.headers['Set-Cookie'].replace(' ', '').split(';')[0]
                self.headers['Cookie'] = cookie
            response = await r.text()
            if not response or r.status > 200:
                if reconnect_on_error:
                    await self.connect_http()
                    await self._request(endpoint, body,
                                        reconnect_on_error=False)
                else:
                    raise IOError(f"Unable to connect with MFC at {self.http_address}")
            return response
