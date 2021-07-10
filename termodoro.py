#!/usr/bin/env python3
import dataclasses
import curses
import math
import time


NANO_PER_SECOND = 1_000_000_000


@dataclasses.dataclass
class Coordinate:
    """A simple coordinate on a 2D X Y plane."""
    x: int
    y: int


class Clock:
    """Represents the main clock.

    :param diameter: the diameter of the clock.
    :param seconds: the duration of the clock in seconds.
    :param hand_length: the length of the hand in proportion to the clock radius (.5 is half the radius). If
        hand_length > 1, the value 1 is used
    """

    def __init__(self, diameter: int, seconds: int, hand_length: float = .5):
        self.diameter = diameter
        self.__radius = diameter // 2

        self.__start_time = time.time_ns()
        self.__nano_seconds = seconds * NANO_PER_SECOND

        self.__hand_length = hand_length

    def coordinates(self) -> list[Coordinate]:
        """Retrieve a list of the curses terminal locations to populate.

        :return: The list of terminal coordinates to populate.
        """
        coords = self.__clock_coordinates()

        if not self.is_done():
            coords += self.__hand_coordinates()

        return coords

    def is_done(self) -> bool:
        """Determine if the specified clock duration as elapsed.

        :return: True is all time has elapsed, False otherwise.
        """
        return time.time_ns() - self.__start_time >= self.__nano_seconds

    def reset(self):
        """Reset the start time of the clock to the current time."""
        self.__start_time = time.time_ns()

    def set_duration(self, seconds: int):
        self.__nano_seconds = seconds * NANO_PER_SECOND

    def seconds_remaining(self) -> int:
        elapsed = time.time_ns() - self.__start_time

        return max(0, math.ceil((self.__nano_seconds - elapsed) / NANO_PER_SECOND))

    def __clock_coordinates(self) -> list[Coordinate]:
        coords = [Coordinate(self.__radius, self.__radius)]
        tolerance = .5

        for y in range(self.diameter + 1):
            for x in range(self.diameter + 1):
                distance = math.sqrt((x - self.__radius) ** 2 + (y - self.__radius) ** 2)

                if self.__radius - tolerance < distance < self.__radius + tolerance:
                    coords.append(Coordinate(x, y))

        return coords

    def __hand_coordinates(self) -> list[Coordinate]:
        time_elapsed = time.time_ns() - self.__start_time
        percent_elapsed = min(time_elapsed / self.__nano_seconds, 1.0)

        slope = Clock.__get_slope(percent_elapsed)

        # find the ranges to limit the search to the proper quadrant
        if percent_elapsed <= .25 or percent_elapsed == 1:
            y_range = range(0, self.__radius + 1)
            x_range = range(self.__radius, self.diameter + 1)
        elif .25 < percent_elapsed <= .5:
            y_range = range(self.__radius, self.diameter + 1)
            x_range = range(self.__radius, self.diameter + 1)
        elif .5 < percent_elapsed <= .75:
            y_range = range(self.__radius, self.diameter + 1)
            x_range = range(0, self.__radius + 1)
        else:
            y_range = range(0, self.__radius + 1)
            x_range = range(0, self.__radius + 1)

        if slope == math.nan:
            x_range = range(self.__radius, self.__radius + 1)

        tolerance = abs(slope) if abs(slope) > .5 else .5
        coords = list()

        for x in x_range:
            centered_x = x - self.__radius

            for y in y_range:
                centered_y = self.__radius - y

                if ((slope == math.nan or centered_y - tolerance < centered_x * slope < centered_y + tolerance) and
                        self.__center_distance(x, y) < self.__radius * self.__hand_length + .5):
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

        # get the 1st quadrant equivalent of the angle (45 -> 135 ->
        # 225 -> 315) which can be used to determine the slope
        first_quad_eq_degrees = degrees - degrees // 90 * 90

        # invert the slope if in the 1st or 3rd quadrant or invert the
        # 1st quadrant angle if in the 2nd or 4th quadrant, this will
        # perform the necessary reflection across the Y axis
        if degrees <= 90 or 180 <= degrees <= 270:
            slope = -math.tan(math.radians(first_quad_eq_degrees)) if first_quad_eq_degrees != 90 else math.nan
        else:
            slope = math.tan(math.radians(90 - first_quad_eq_degrees)) if first_quad_eq_degrees != 0 else math.nan

        return slope


class SessionState:
    """Tracks the session state."""

    def __init__(self, work_duration: int, short_duration: int, long_duration: int, before_long: int):
        self.__before_long = before_long

        self.__work_duration = work_duration
        self.__short_duration = long_duration
        self.__long_duration = short_duration

        self.__round = 1

    def get_work(self) -> int:
        self.__round += 1

        return self.__work_duration

    def get_break(self) -> int:
        if self.next_long() == 0:
            return self.__long_duration
        else:
            return self.__short_duration

    def next_long(self) -> int:
        """Get the amount of work rounds until the next long break."""
        if self.__before_long > self.__round:
            return self.__before_long - self.__round
        else:
            return self.__round % self.__before_long

    def completed(self) -> int:
        """Get the amount of completed work periods."""
        return self.__round - 1


class SessionDisplay:
    __MIN_CLOCK_DIAMETER = 5

    def __init__(self, screen, show_completed: bool = True, show_next_long: bool = True, show_digital: bool = True,
                 show_analog: bool = True, bg_color: str = 'white"'):
        self.__screen = screen

        self.__show_completed = show_completed
        self.__show_next_long = show_next_long
        self.__show_digital = show_digital
        self.__show_analog = show_analog

        self.__bg_color = bg_color

    def redraw(self, clock: Clock, state: SessionState):
        self.__screen.clear()

        x_padding = 0
        y_padding = 0

        if self.__show_analog:
            x_padding = clock.diameter

            for coord in clock.coordinates():
                self.__screen.addch(coord.y, coord.x, ' ', curses.color_pair(1))

        if self.__show_completed:
            self.__screen.addstr(y_padding, x_padding, f"Rounds completed: {state.completed()}")
            y_padding += 1

        if self.__show_next_long:
            self.__screen.addstr(y_padding, x_padding, f"Next long break in {state.next_long()} round{'s' if state.next_long() > 1 else ''}")
            y_padding += 1

        if self.__show_digital:
            self.__screen.addstr(y_padding, x_padding,
                                 f"Time remaining: {SessionDisplay.__remaining_time_str(clock.seconds_remaining())}s")
            y_padding += 1

        self.__screen.refresh()

    @staticmethod
    def __remaining_time_str(remaining_seconds: int):
        """Get the string describing how much time is left based on the amount of remaining seconds.

        (ex) remaining_time_Str(61) = "01:01"

        :param: the amount of seconds remaining in the current round.
        :return: a string representation of the remaining time left.
        """
        minutes = math.ceil(remaining_seconds // 60)
        seconds = remaining_seconds - minutes * 60

        return f"{minutes:02}:{seconds:02}"


def main(screen):
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_WHITE)
    screen.clear()

    display = SessionDisplay(screen)

    clock = Clock(50, 5, .5)
    state = SessionState(25, 5, 15, 4)

    try:
        while True:
            display.redraw(clock, state)
            time.sleep(.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    # main(None)
    curses.wrapper(main)

