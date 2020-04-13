mfc
===

Python driver and command-line tool for [Brooks Instrument mass flow controllers](https://www.brooksinstrument.com/en/products/mass-flow-controllers).

<p align="center">
  <img height="250" src="https://www.brooksinstrument.com/~/media/brooks/images/products/mass%20flow%20controllers/metal%20sealed/gf100/gf100-gf120-gf125-mass-flow-controller-3-491px.png" />
</p>

Installation
============

```
pip install brooks_mfc
```

Usage
=====

This driver uses an undocumented REST API in the devices's web interface for communication.
The compatibility and stability of this interface with all Brooks controllers is not guaranteed.

### Command Line

To test your connection and stream real-time data, use the command-line
interface. You can read the flow rate with:

```
$ brooks-mfc 192.168.1.200
{
    "Customer Flow Totalizer": 0.0,
    "Flow": -0.3,
    "Flow Hours": 1.0,
    "Flow Totalizer": 0.0,
    "Live Setpoint": 0.0,
    "Operational Hours": 50.0,
    "Setpoint": 0.0,
    "Supply Voltage": 22.93,
    "Temperature": 27.11,
    "Valve Position": 0.0
}
```

You can optionally specify a setpoint flow with:
`brooks-mfc 192.168.1.150 --set 7.5. See `mfc --help` for more.

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

The API that matters is `get`, `set`.

```python
>>> await fc.get()
{
    "Customer Flow Totalizer": 0.0,
    "Flow": -0.3,
    "Flow Hours": 1.0,
    "Flow Totalizer": 0.0,
    "Live Setpoint": 0.0,
    "Operational Hours": 50.0,
    "Setpoint": 0.0,
    "Supply Voltage": 22.93,
    "Temperature": 27.11,
    "Valve Position": 0.0
}
```
```python
>>> await fc.set(10)
>>> await fc.open()   # set to max flow
>>> await fc.close()  # set to zero flow
```