"""
Python driver for Brooks Instrument flow controllers.
Distributed under the GNU General Public License v2
Copyright (C) 2020 NuMat Technologies
"""
from brooks_mfc.driver import FlowController


def command_line():
    """Command-line tool for MKS mass flow controllers."""
    import argparse
    import asyncio
    import json
    import sys
    red, reset = '\033[1;31m', '\033[0m'

    parser = argparse.ArgumentParser(description="Control an Brooks Instrument MFC "
                                                 "from the command line.")
    parser.add_argument('address', help="The IP address of the MFC")
    parser.add_argument('--set', '-s', default=None, type=float,
                        help="Sets the setpoint flow of the mass flow controller, "
                             "in units specified in the manual (likely sccm).")
    args = parser.parse_args()

    async def run():
        try:
            async with FlowController(args.address) as fc:
                if args.set is not None:
                    await fc.set(args.set)
                    await asyncio.sleep(0.1)
                print(json.dumps(await fc.get(), indent=4, sort_keys=True))
        except asyncio.TimeoutError:
            sys.stderr.write(f'{red}Could not connect to device.{reset}\n')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
    loop.close()


if __name__ == '__main__':
    command_line()
