import operator
from datetime import datetime, timezone

from dateutil.parser import parse as parse_date


class Date:
    """
    Common datetime usage
    """

    def __init__(self, date: datetime) -> None:
        self.date = date
        if not self.date.tzinfo:
            self.date = self.date.astimezone(tz=timezone.utc)

    @property
    def utc(self) -> datetime:
        """
        Returns the date in UTC timezone.
        """
        return self.date.astimezone(tz=timezone.utc)

    @property
    def local(self) -> datetime:
        """
        Returns the date in the local timezone.
        """
        return self.date.astimezone()

    def compare_to(self, date: datetime, operation: str) -> bool:
        """
        Compares the date with the input date using the specified operation.

        Parameters:
        - date: The datetime object to compare with.
        - operation: The comparison operation (==, !=, <=, >=, <, >).

        Returns:
        - True if the comparison result is True, False otherwise.
        """
        ops = {
            "==": operator.eq,
            "!=": operator.ne,
            "<=": operator.le,
            ">=": operator.ge,
            "<": operator.lt,
            ">": operator.gt,
        }
        if not ops.get(operation):
            raise ArithmeticError(f"No such operation {operation}, available is {*ops.keys(),}")
        if not date.tzinfo:
            date = date.astimezone(timezone.utc)
        return ops[operation](self.date.astimezone(date.tzinfo), date)

    @classmethod
    def now(cls):
        """
        Creates a Date instance with the current datetime.
        """
        return cls(datetime.now().astimezone())

    @classmethod
    def from_string(cls, date: str):
        """
        Creates a Date instance from a string using the `dateutil.parser.parse` function.

        Parameters:
        - date: String representation of the date.
        """
        return cls(parse_date(date))

    @classmethod
    def from_timestamp(cls, timestamp: int):
        """
        Creates a Date instance from a timestamp, considering it as UTC timestamp.

        Parameters:
        - timestamp: UTC timestamp.
        """
        date = datetime.utcfromtimestamp(timestamp)
        return cls(date)
