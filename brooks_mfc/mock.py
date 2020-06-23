import random

import asyncio
from collections import defaultdict
from unittest.mock import MagicMock


class AsyncMock(MagicMock):
    """Magic mock that works with async methods"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


class FlowController(AsyncMock):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = defaultdict(float)
        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self._perturb())

    async def _perturb(self):
        while True:
            await asyncio.sleep(1)
            self.state['Live Setpoint'] += round(
                (self.state['Setpoint'] - self.state['Live Setpoint'])/2, 2)
            self.state['Valve Position'] += round(
                (self.state['Live Setpoint'] - self.state['Valve Position'])
                / 2, 2)
            self.state['Flow'] += round(
                (self.state['Valve Position'] - self.state['Flow']) / 2, 2)
            if self.state['Flow']:
                self.state['Flow Hours'] += 0.01
            self.state['Flow Totalizer'] += self.state['Flow'] * 50
            self.state['Customer Flow Totalizer'] = self.state[
                'Flow Totalizer']
            self.state['Operational Hours'] += 0.01
            self.state['Temperature'] = 23 + random.random()
            self.state['Supply Voltage'] = 23 + random.random()

    async def get(self, units: str = None):
        await asyncio.sleep(0.1)
        return self.state

    async def set(self, setpoint: float, units: str = None):
        await asyncio.sleep(0.2)
        self.state['Setpoint'] = setpoint
