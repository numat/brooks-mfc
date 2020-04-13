mfc
===

Python driver and command-line tool for [Brooks Instrument mass flow controllers](https://www.brooksinstrument.com/en/products/mass-flow-controllers).

<p align="center">
  <img height="250" src="https://www.brooksinstrument.com/~/media/brooks/images/products/mass%20flow%20controllers/metal%20sealed/gf100/gf100-gf120-gf125-mass-flow-controller-3-491px.png" />
</p>

Installation
============

```
pip install mfc
```

Usage
=====

This driver uses an undocumented REST API in the devices's web interface for communication.
The compatibility and stability of this interface with all Brooks conrtollers is not guaranteed.

### Command Line

To test your connection and stream real-time data, use the command-line
interface. You can read the flow rate with:

```
$ brooks-mfc 192.168.1.200
{
  "actual": 4.99,
  "gas": "CO2",
  "max": 37,
  "setpoint": 5.00,
  "temperature": 27.34
}
```

You can optionally specify a setpoint flow with:
`mfc 192.168.1.150 --set 7.5. See `mfc --help` for more.

### Python

This uses Python ≥3.5's async/await syntax to asynchronously communicate with
the mass flow controller. For example:

```python
import asyncio
from brooks_mfc import FlowController

async def get():
    async with FlowController('the-mfc-ip-address') as fc:
        print(await fc.get())

asyncio.run(get())
```

The API that matters is `get`, `set`, and `set_gas`.

```python
>>> await fc.get()
{
  "actual": 4.99,
  "gas": "CO2",
  "max": 37,
  "setpoint": 5.00,
  "temperature": 27.34
}
```
```python
>>> await fc.set(10)
>>> await fc.open()   # set to max flow
>>> await fc.close()  # set to zero flow
```