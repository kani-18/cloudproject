import math


def position_error(actual, twin):
    dx = actual["x"] - twin["x"]
    dy = actual["y"] - twin["y"]
    return math.hypot(dx, dy)


def speed_error(actual, twin):
    return abs(actual["speed"] - twin["speed"])


def heading_error(actual, twin):
    difference = actual["heading"] - twin["heading"]
    return abs((difference + 180.0) % 360.0 - 180.0)
