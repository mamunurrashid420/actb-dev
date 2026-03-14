"""Decorators for asset execution logging and error handling."""

from collections.abc import Callable
from functools import wraps
from typing import Any

import dagster as dg


def log_asset_execution(operation: str | None = None):
    """Log asset execution start/end."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(context: dg.AssetExecutionContext, *args, **kwargs):
            asset_name = context.asset_key.path[-1]
            op = operation or f"Processing {asset_name}"

            context.log.info(f"{op} - starting...")
            try:
                result = func(context, *args, **kwargs)
                context.log.info(f"{op} - complete")
                return result
            except Exception as e:
                context.log.error(f"{op} - failed: {str(e)}")
                raise RuntimeError(f"{op} failed") from e

        return wrapper

    return decorator


def handle_asset_errors(default_return: Any = None, reraise: bool = True):
    """Handle and log asset execution errors."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(context: dg.AssetExecutionContext, *args, **kwargs):
            try:
                return func(context, *args, **kwargs)
            except Exception as e:
                context.log.error(f"Error in {context.asset_key.path[-1]}: {str(e)}")
                if reraise:
                    raise RuntimeError(f"Error in {context.asset_key.path[-1]}") from e
                return default_return

        return wrapper

    return decorator
