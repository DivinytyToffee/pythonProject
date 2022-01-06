import datetime


def time_to_planet(distance: int, speed: int):
    km = distance * 149597870.7
    _time = km/speed
    return str(datetime.timedelta(seconds=_time))


if __name__ == '__main__':
    print(time_to_planet(80, 2500))
