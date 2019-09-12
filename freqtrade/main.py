#!/usr/bin/env python3
"""
Main Freqtrade bot script.
Read the documentation to know what cli arguments you need.
"""

import sys
# check min. python version
if sys.version_info < (3, 6):
    sys.exit("Freqtrade requires Python version >= 3.6")

# flake8: noqa E402
import logging
from typing import Any, List

from freqtrade import OperationalException
from freqtrade.configuration import Arguments
from freqtrade.worker import Worker


logger = logging.getLogger('freqtrade')


def main(sysargv: List[str] = None) -> None:
    """
    This function will initiate the bot and start the trading loop.
    :return: None
    """

    return_code: Any = 1
    worker = None
    try:
        arguments = Arguments(sysargv)
        args = arguments.get_parsed_arg()

        # A subcommand has been issued.
        # Means if Backtesting or Hyperopt have been called we exit the bot
        if 'func' in args:
            args['func'](args)
            # TODO: fetch return_code as returned by the command function here
            return_code = 0
        else:
            # Load and run worker
            worker = Worker(args)
            worker.run()

    except SystemExit as e:
        return_code = e
    except KeyboardInterrupt:
        logger.info('SIGINT received, aborting ...')
        return_code = 0
    except OperationalException as e:
        logger.error(str(e))
        return_code = 2
    except Exception:
        logger.exception('Fatal exception!')
    finally:
        if worker:
            worker.exit()
        sys.exit(return_code)


if __name__ == '__main__':
    main()
