"""Mutable value holder (Arduino float* / String* equivalent)."""


class Ref:
    """Hold a value that write()/read() can update in place.

    Example::

        sensor = Ref(0.0)
        IOTFIY.write("SensorValue", "float", "A0", sensor)
        sensor.value = 42.5
        IOTFIY.launch()
    """

    __slots__ = ("value",)

    def __init__(self, value=0.0):
        self.value = value

    def __repr__(self):
        return f"Ref({self.value!r})"
