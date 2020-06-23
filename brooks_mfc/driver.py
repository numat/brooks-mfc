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

STATUS_CODE = {'Fl': 'Flow', 'SP': 'Setpoint', 'LSP': 'LiveSetpoint',
                'VP': 'ValvePosition', 'TP': 'Temperature',
                'Tot': 'FlowTotalizer', 'Ctot': 'CustomerFlowTotalizer',
                'Hrs': 'FlowHours', 'OpHrs': 'OperationalHours',
                'Volt': 'SupplyVoltage'}

UNIT_CODES = {
  'bbl/day':      2072,
  'bbl/hr':       2071,
  'bbl/min':      2070,
  'bbl/sec':      2069,
  'cc/day':       2051,
  'cc/hr':        2050,
  'cc/min':       2049,
  'cc/sec':       2048,
  'cu ft/day':    2059,
  'cu ft/hr':     2058,
  'cu ft/min':    5122,
  'cu ft/sec':    2057,
  'gal/day':      2064,
  'gal/hr':       5130,
  'gal/min':      5129,
  'gal/sec':      5128,
  'g/day':        2075,
  'g/hr':         2074,
  'g/min':        5135,
  'g/sec':        2073,
  'imp gal/day':  2068,
  'imp gal/hr':   2067,
  'imp gal/min':  2066,
  'imp gal/sec':  2065,
  'cu in/day':    2063,
  'cu in/hr':     2062,
  'cu in/min':    2061,
  'cu in/sec':    2060,
  'kg/day':       2077,
  'kg/hr':        5136,
  'kg/min':       2076,
  'kg/sec':       5124,
  'lbs/day':      2078,
  'lbs/hr':       5133,
  'lbs/min':      5132,
  'lbs/sec':      5131,
  'L/day':        2053,
  'L/hr':         5140,
  'L/min':        5139,
  'L/sec':        5126,
  'm3/day':       2056,
  'm3/hr':        2055,
  'm3/min':       2054,
  'm3/sec':       5125,
  'mL/day':       2052,
  'mL/hr':        5138,
  'mL/min':       5137,
  'mL/sec':       5127,
  'oz/day':       2082,
  'oz/hr':        2081,
  'oz/min':       2080,
  'oz/sec':       2079,
  '%':            4103,
  'percent':      4103,
  'sccm':         5120,
  'slpm':         5121
}


class FlowController(object):
    """Driver for Brooks Instrument mass flow controllers."""

    def __init__(self, address: str, timeout: float = 10,
                 password: str = 'control'):
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

    async def get(self, units: str = None):
        """Retrieve the device state.

        This is done using a websocket interface.

        Args:
            units: The units for the flow meter. If blank use existing units.
        """
        await self._set_units(units, 'flow')
        if not self.web_socket:
            await self.connect_ws()
        await self.web_socket.send_str('A')
        response = await self.web_socket.receive_json()
        return {STATUS_CODE[k]: float(v) for k, v in response.items()
                if k in STATUS_CODE}

    async def set(self, setpoint: float, units: str = None):
        """Set the setpoint flow rate, in percent.

        This uses an undocumented HTTP extension, `Control.html`.

        Args:
            setpoint: Setpoint flow, as a float.
            units: The units for the setpoint. If blank use existing units.
        """
        await self._set_units(units, 'setpoint')
        await self._request('Control.html', {0: setpoint})

    async def set_units(self, units=None, target='flow'):
        """Set the flow meter units"""
        if units is None:
            return
        index = ['flow', 'setpoint'].index(target)
        try:
            await self._request('Units.html',
                                {index: UNIT_CODES[units.lower()]})
        except IndexError:
            raise ValueError(
                f"{units} is not a valid unit for this flow controller")

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
