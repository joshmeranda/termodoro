#!/usr/bin/env python3
from abc import ABC
import dataclasses
import curses
import math
import time


@dataclasses.dataclass
class Coordinate:
    """A simple coordinate on a 2D X Y plane."""
    x: int
    y: int


class ClockProvider:
    """Represents the main clock.

    :param radius: the radius of the clock.
    :param seconds: the amount of seconds for the clock.
    """

    def __init__(self, radius: int, seconds: int):
        self.__radius = radius
        self.__diameter = radius * 2 + 1
        self.__start_time = time.time_ns()
        self.__nano_seconds = seconds * 1_000_000_000

    def coordinates(self) -> list[Coordinate]:
        clock_coords = self.__perimeter_coordinates()
        hand_coords = self.__hand_coordinates()

        return clock_coords + hand_coords

    def __perimeter_coordinates(self) -> list[Coordinate]:
        coords = [Coordinate(self.__radius, self.__radius)]
        tolerance = .5

        for y in range(self.__diameter):
            for x in range(self.__diameter):
                distance = math.sqrt((x - self.__radius) ** 2 + (y - self.__radius) ** 2)

                if self.__radius - tolerance < distance < self.__radius + tolerance:
                    coords.append(Coordinate(x, y))

        return coords

    def __hand_coordinates(self) -> list[Coordinate]:
        time_elapsed = time.time_ns() - self.__start_time
        percent_elapsed = time_elapsed / self.__nano_seconds if time_elapsed < self.__nano_seconds else 1.0

        slope = ClockProvider.__get_slope(percent_elapsed)

        # find the ranges to limit the search to the proper quadrant
        if percent_elapsed <= .25 or percent_elapsed == 1:
            y_range = range(0, self.__radius + 1)
            x_range = range(self.__radius, self.__diameter + 1)
        elif .25 < percent_elapsed <= .5:
            y_range = range(self.__radius, self.__diameter + 1)
            x_range = range(self.__radius, self.__diameter + 1)
        elif .5 < percent_elapsed <= .75:
            y_range = range(self.__radius, self.__diameter + 1)
            x_range = range(0, self.__radius + 1)
        else:
            y_range = range(0, self.__radius + 1)
            x_range = range(0, self.__radius + 1)

        if slope == math.nan:
            x_range = range(self.__radius, self.__radius + 1)

        tolerance = abs(slope) if abs(slope) > .5 else .5
        coords = list()
        hand_length = self.__radius * .5

        for x in x_range:
            centered_x = x - self.__radius

            for y in y_range:
                centered_y = self.__radius - y

                if ((slope == math.nan or centered_y - tolerance < centered_x * slope < centered_y + tolerance) and
                        self.__center_distance(x, y) < hand_length + .5):
                    coords.append(Coordinate(x, y))

        return coords

    def __center_distance(self, x, y) -> float:
        return math.sqrt((x - self.__radius) ** 2 + (y - self.__radius) ** 2)

    @staticmethod
    def __get_slope(percent_elapsed: float) -> float:
        """Get the slope of the clock hand given the amount of time that has passed as a ratio.

        :param percent_elapsed: the amount of time that has passed (total time / elapsed time).
        :return: the slope of the clock hand as a float or, math.nan if the slope is a vertical line.
        """
        degrees = percent_elapsed * 360

        # shift the angle since 0 seconds should point to 90 rather
        # than 0, the hand angle must still be reflected across the Y
        # axes but that will be handled later
        degrees += 90 if degrees <= 270 else -270

        # get the first quadrant equivalent of the angle (45 -> 135 ->
        # 225 -> 315) which can be used to determine the slope
        first_quad_eq_degrees = degrees - degrees // 90 * 90

        # invert the slope if in the first or third quadrant, this will
        # perform the necessary reflection across the Y axis
        if degrees <= 90 or 180 <= degrees <= 270:
            slope = -math.tan(math.radians(first_quad_eq_degrees)) if first_quad_eq_degrees != 90 else math.nan
        else:
            slope = math.tan(math.radians(90 - first_quad_eq_degrees)) if first_quad_eq_degrees != 0 else math.nan

        return slope


def main(screen):
    try:
        import os
        os.remove("out")
    except FileNotFoundError or PermissionError:
        pass

    clock = ClockProvider(25, 60)

    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_WHITE)
    screen.clear()

    try:
        while True:
            screen.clear()
            for coord in clock.coordinates():
                screen.addstr(coord.y, coord.x, ' ', curses.color_pair(1))
            screen.refresh()
            time.sleep(.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    # main(None)
    curses.wrapper(main)

