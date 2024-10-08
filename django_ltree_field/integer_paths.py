import string

# Postgres 16 and later
# For example, in C locale, the characters A-Za-z0-9_- are allowed. Labels must be no more than 1000 characters long.
# # Postgres 15
# A label is a sequence of alphanumeric characters and underscores (for example, in C locale the characters A-Za-z0-9_ are allowed). Labels must be less than 256 characters long.


class Codec:
    def __init__(self, version: int = 16):
        if version >= 16:
            self.chars = (
                "-"
                + string.digits
                + string.ascii_uppercase
                + "_"
                + string.ascii_lowercase
            )
            self.base = len(self.chars)
            self.max_value = self.base**1000 - 1
        else:
            self.chars = (
                string.digits + string.ascii_uppercase + "_" + string.ascii_lowercase
            )
            self.base = len(self.chars)
            self.max_value = self.base**255 - 1

    def encode(self, value: int) -> str:
        if value == 0:
            return self.chars[0]

        if value < 0 or value > self.max_value:
            msg = f"Value must be between 0 and {self.max_value}"
            raise ValueError(msg)

        result: list[str] = []
        while value > 0:
            value, remainder = divmod(value, self.base)
            result.append(self.chars[remainder])

        return "".join(reversed(result))

    def decode(self, value: str) -> int:
        result = 0
        for char in value:
            result = result * self.base + self.chars.index(char)
        return result


# CHARS = "-" + string.digits + string.ascii_uppercase + "_" + string.ascii_lowercase

# BASE = len(CHARS)

# MAX_VALUE = BASE**1000 - 1


# def encode(value: int) -> str:
#     if value == 0:
#         return CHARS[0]

#     if value < 0 or value > MAX_VALUE:
#         msg = f"Value must be between 0 and {MAX_VALUE}"
#         raise ValueError(msg)

#     result: list[str] = []
#     while value > 0:
#         value, remainder = divmod(value, BASE)
#         result.append(CHARS[remainder])

#     return "".join(reversed(result))


# def decode(value: str) -> int:
#     result = 0
#     for char in value:
#         result = result * BASE + CHARS.index(char)
#     return result
