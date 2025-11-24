import logging

logger = logging.getLogger(__name__)


def parse_time(time_str: str) -> float:
    """
    Parses a time string in format "HH:MM:SS" or "MM:SS" into seconds.

    Args:
        time_str: The time string to parse.

    Returns:
        The time in seconds as a float.

    Raises:
        ValueError: If the format is incorrect.
    """
    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        else:
            raise ValueError(
                f"Invalid time format: {time_str}. Expected HH:MM:SS or MM:SS"
            )
    except ValueError as e:
        logger.error(f"Failed to parse time string '{time_str}': {e}")
        raise
