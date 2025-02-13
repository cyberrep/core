"""The test for weather entity."""
from datetime import datetime

import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.weather import (
    ATTR_CONDITION_SUNNY,
    ATTR_FORECAST,
    ATTR_FORECAST_APPARENT_TEMP,
    ATTR_FORECAST_DEW_POINT,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRESSURE,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_UV_INDEX,
    ATTR_FORECAST_WIND_GUST_SPEED,
    ATTR_FORECAST_WIND_SPEED,
    ATTR_WEATHER_APPARENT_TEMPERATURE,
    ATTR_WEATHER_OZONE,
    ATTR_WEATHER_PRECIPITATION_UNIT,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_PRESSURE_UNIT,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_TEMPERATURE_UNIT,
    ATTR_WEATHER_UV_INDEX,
    ATTR_WEATHER_VISIBILITY,
    ATTR_WEATHER_VISIBILITY_UNIT,
    ATTR_WEATHER_WIND_BEARING,
    ATTR_WEATHER_WIND_GUST_SPEED,
    ATTR_WEATHER_WIND_SPEED,
    ATTR_WEATHER_WIND_SPEED_UNIT,
    DOMAIN,
    LEGACY_SERVICE_GET_FORECAST,
    ROUNDING_PRECISION,
    SERVICE_GET_FORECASTS,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
    round_temperature,
)
from homeassistant.components.weather.const import (
    ATTR_WEATHER_CLOUD_COVERAGE,
    ATTR_WEATHER_DEW_POINT,
    ATTR_WEATHER_HUMIDITY,
)
from homeassistant.const import (
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.issue_registry as ir
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import (
    DistanceConverter,
    PressureConverter,
    SpeedConverter,
    TemperatureConverter,
)
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM

from . import MockWeatherTest, create_entity

from tests.typing import WebSocketGenerator


class MockWeatherEntity(WeatherEntity):
    """Mock a Weather Entity."""

    def __init__(self) -> None:
        """Initiate Entity."""
        super().__init__()
        self._attr_condition = ATTR_CONDITION_SUNNY
        self._attr_native_precipitation_unit = UnitOfLength.MILLIMETERS
        self._attr_native_pressure = 10
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_native_temperature = 20
        self._attr_native_apparent_temperature = 25
        self._attr_native_dew_point = 2
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_native_visibility = 30
        self._attr_native_visibility_unit = UnitOfLength.KILOMETERS
        self._attr_native_wind_gust_speed = 10
        self._attr_native_wind_speed = 3
        self._attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
        self._attr_forecast = [
            Forecast(
                datetime=datetime(2022, 6, 20, 00, 00, 00, tzinfo=dt_util.UTC),
                native_precipitation=1,
                native_temperature=20,
                native_dew_point=2,
            )
        ]
        self._attr_forecast_twice_daily = [
            Forecast(
                datetime=datetime(2022, 6, 20, 8, 00, 00, tzinfo=dt_util.UTC),
                native_precipitation=10,
                native_temperature=25,
            )
        ]


@pytest.mark.parametrize(
    "native_unit", (UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.CELSIUS)
)
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfTemperature.CELSIUS, METRIC_SYSTEM),
        (UnitOfTemperature.FAHRENHEIT, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_temperature(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test temperature."""
    hass.config.units = unit_system
    native_value = 38
    apparent_native_value = 45
    dew_point_native_value = 32
    state_value = TemperatureConverter.convert(native_value, native_unit, state_unit)
    apparent_state_value = TemperatureConverter.convert(
        apparent_native_value, native_unit, state_unit
    )

    state_value = TemperatureConverter.convert(native_value, native_unit, state_unit)
    dew_point_state_value = TemperatureConverter.convert(
        dew_point_native_value, native_unit, state_unit
    )

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_temperature": native_value,
        "native_temperature_unit": native_unit,
        "native_apparent_temperature": apparent_native_value,
        "native_dew_point": dew_point_native_value,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast_daily = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    apparent_expected = apparent_state_value
    dew_point_expected = dew_point_state_value
    assert float(state.attributes[ATTR_WEATHER_TEMPERATURE]) == pytest.approx(
        expected, rel=0.1
    )
    assert float(state.attributes[ATTR_WEATHER_APPARENT_TEMPERATURE]) == pytest.approx(
        apparent_expected, rel=0.1
    )
    assert float(state.attributes[ATTR_WEATHER_DEW_POINT]) == pytest.approx(
        dew_point_expected, rel=0.1
    )
    assert state.attributes[ATTR_WEATHER_TEMPERATURE_UNIT] == state_unit
    assert float(forecast_daily[ATTR_FORECAST_TEMP]) == pytest.approx(expected, rel=0.1)
    assert float(forecast_daily[ATTR_FORECAST_APPARENT_TEMP]) == pytest.approx(
        apparent_expected, rel=0.1
    )
    assert float(forecast_daily[ATTR_FORECAST_DEW_POINT]) == pytest.approx(
        dew_point_expected, rel=0.1
    )
    assert float(forecast_daily[ATTR_FORECAST_TEMP_LOW]) == pytest.approx(
        expected, rel=0.1
    )
    assert float(forecast_daily[ATTR_FORECAST_TEMP]) == pytest.approx(expected, rel=0.1)
    assert float(forecast_daily[ATTR_FORECAST_TEMP_LOW]) == pytest.approx(
        expected, rel=0.1
    )


@pytest.mark.parametrize("native_unit", (None,))
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfTemperature.CELSIUS, METRIC_SYSTEM),
        (UnitOfTemperature.FAHRENHEIT, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_temperature_no_unit(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test temperature when the entity does not declare a native unit."""
    hass.config.units = unit_system
    native_value = 38
    dew_point_native_value = 32
    apparent_temp_native_value = 45
    state_value = native_value
    dew_point_state_value = dew_point_native_value
    apparent_temp_state_value = apparent_temp_native_value

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_temperature": native_value,
        "native_temperature_unit": native_unit,
        "native_dew_point": dew_point_native_value,
        "native_apparent_temperature": apparent_temp_native_value,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    dew_point_expected = dew_point_state_value
    expected_apparent_temp = apparent_temp_state_value
    assert float(state.attributes[ATTR_WEATHER_TEMPERATURE]) == pytest.approx(
        expected, rel=0.1
    )
    assert float(state.attributes[ATTR_WEATHER_DEW_POINT]) == pytest.approx(
        dew_point_expected, rel=0.1
    )
    assert float(state.attributes[ATTR_WEATHER_APPARENT_TEMPERATURE]) == pytest.approx(
        expected_apparent_temp, rel=0.1
    )
    assert state.attributes[ATTR_WEATHER_TEMPERATURE_UNIT] == state_unit
    assert float(forecast[ATTR_FORECAST_TEMP]) == pytest.approx(expected, rel=0.1)
    assert float(forecast[ATTR_FORECAST_DEW_POINT]) == pytest.approx(
        dew_point_expected, rel=0.1
    )
    assert float(forecast[ATTR_FORECAST_TEMP_LOW]) == pytest.approx(expected, rel=0.1)
    assert float(forecast[ATTR_FORECAST_APPARENT_TEMP]) == pytest.approx(
        expected_apparent_temp, rel=0.1
    )


@pytest.mark.parametrize("native_unit", (UnitOfPressure.INHG, UnitOfPressure.INHG))
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    ((UnitOfPressure.HPA, METRIC_SYSTEM), (UnitOfPressure.INHG, US_CUSTOMARY_SYSTEM)),
)
async def test_pressure(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test pressure."""
    hass.config.units = unit_system
    native_value = 30
    state_value = PressureConverter.convert(native_value, native_unit, state_unit)

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {"native_pressure": native_value, "native_pressure_unit": native_unit}

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    assert float(state.attributes[ATTR_WEATHER_PRESSURE]) == pytest.approx(
        expected, rel=1e-2
    )
    assert float(forecast[ATTR_FORECAST_PRESSURE]) == pytest.approx(expected, rel=1e-2)


@pytest.mark.parametrize("native_unit", (None,))
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    ((UnitOfPressure.HPA, METRIC_SYSTEM), (UnitOfPressure.INHG, US_CUSTOMARY_SYSTEM)),
)
async def test_pressure_no_unit(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test pressure when the entity does not declare a native unit."""
    hass.config.units = unit_system
    native_value = 30
    state_value = native_value

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {"native_pressure": native_value, "native_pressure_unit": native_unit}

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    assert float(state.attributes[ATTR_WEATHER_PRESSURE]) == pytest.approx(
        expected, rel=1e-2
    )
    assert float(forecast[ATTR_FORECAST_PRESSURE]) == pytest.approx(expected, rel=1e-2)


@pytest.mark.parametrize(
    "native_unit",
    (
        UnitOfSpeed.MILES_PER_HOUR,
        UnitOfSpeed.KILOMETERS_PER_HOUR,
        UnitOfSpeed.METERS_PER_SECOND,
    ),
)
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfSpeed.KILOMETERS_PER_HOUR, METRIC_SYSTEM),
        (UnitOfSpeed.MILES_PER_HOUR, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_wind_speed(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test wind speed."""
    hass.config.units = unit_system
    native_value = 10
    state_value = SpeedConverter.convert(native_value, native_unit, state_unit)

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {"native_wind_speed": native_value, "native_wind_speed_unit": native_unit}

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    assert float(state.attributes[ATTR_WEATHER_WIND_SPEED]) == pytest.approx(
        expected, rel=1e-2
    )
    assert float(forecast[ATTR_FORECAST_WIND_SPEED]) == pytest.approx(
        expected, rel=1e-2
    )


@pytest.mark.parametrize(
    "native_unit",
    (
        UnitOfSpeed.MILES_PER_HOUR,
        UnitOfSpeed.KILOMETERS_PER_HOUR,
        UnitOfSpeed.METERS_PER_SECOND,
    ),
)
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfSpeed.KILOMETERS_PER_HOUR, METRIC_SYSTEM),
        (UnitOfSpeed.MILES_PER_HOUR, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_wind_gust_speed(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test wind speed."""
    hass.config.units = unit_system
    native_value = 10
    state_value = SpeedConverter.convert(native_value, native_unit, state_unit)

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_wind_gust_speed": native_value,
        "native_wind_speed_unit": native_unit,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    assert float(state.attributes[ATTR_WEATHER_WIND_GUST_SPEED]) == pytest.approx(
        expected, rel=1e-2
    )
    assert float(forecast[ATTR_FORECAST_WIND_GUST_SPEED]) == pytest.approx(
        expected, rel=1e-2
    )


@pytest.mark.parametrize("native_unit", (None,))
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfSpeed.KILOMETERS_PER_HOUR, METRIC_SYSTEM),
        (UnitOfSpeed.MILES_PER_HOUR, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_wind_speed_no_unit(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test wind speed when the entity does not declare a native unit."""
    hass.config.units = unit_system
    native_value = 10
    state_value = native_value

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {"native_wind_speed": native_value, "native_wind_speed_unit": native_unit}

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    assert float(state.attributes[ATTR_WEATHER_WIND_SPEED]) == pytest.approx(
        expected, rel=1e-2
    )
    assert float(forecast[ATTR_FORECAST_WIND_SPEED]) == pytest.approx(
        expected, rel=1e-2
    )


@pytest.mark.parametrize("native_unit", (UnitOfLength.MILES, UnitOfLength.KILOMETERS))
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfLength.KILOMETERS, METRIC_SYSTEM),
        (UnitOfLength.MILES, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_visibility(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test visibility."""
    hass.config.units = unit_system
    native_value = 10
    state_value = DistanceConverter.convert(native_value, native_unit, state_unit)

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {"native_visibility": native_value, "native_visibility_unit": native_unit}

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    expected = state_value
    assert float(state.attributes[ATTR_WEATHER_VISIBILITY]) == pytest.approx(
        expected, rel=1e-2
    )


@pytest.mark.parametrize("native_unit", (None,))
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfLength.KILOMETERS, METRIC_SYSTEM),
        (UnitOfLength.MILES, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_visibility_no_unit(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test visibility when the entity does not declare a native unit."""
    hass.config.units = unit_system
    native_value = 10
    state_value = native_value

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {"native_visibility": native_value, "native_visibility_unit": native_unit}

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    expected = state_value
    assert float(state.attributes[ATTR_WEATHER_VISIBILITY]) == pytest.approx(
        expected, rel=1e-2
    )


@pytest.mark.parametrize("native_unit", (UnitOfLength.INCHES, UnitOfLength.MILLIMETERS))
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfLength.MILLIMETERS, METRIC_SYSTEM),
        (UnitOfLength.INCHES, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_precipitation(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test precipitation."""
    hass.config.units = unit_system
    native_value = 30
    state_value = DistanceConverter.convert(native_value, native_unit, state_unit)

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_precipitation": native_value,
        "native_precipitation_unit": native_unit,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    assert float(forecast[ATTR_FORECAST_PRECIPITATION]) == pytest.approx(
        expected, rel=1e-2
    )


@pytest.mark.parametrize("native_unit", (None,))
@pytest.mark.parametrize(
    ("state_unit", "unit_system"),
    (
        (UnitOfLength.MILLIMETERS, METRIC_SYSTEM),
        (UnitOfLength.INCHES, US_CUSTOMARY_SYSTEM),
    ),
)
async def test_precipitation_no_unit(
    hass: HomeAssistant,
    config_flow_fixture: None,
    native_unit: str,
    state_unit: str,
    unit_system,
) -> None:
    """Test precipitation when the entity does not declare a native unit."""
    hass.config.units = unit_system
    native_value = 30
    state_value = native_value

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_precipitation": native_value,
        "native_precipitation_unit": native_unit,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = state_value
    assert float(forecast[ATTR_FORECAST_PRECIPITATION]) == pytest.approx(
        expected, rel=1e-2
    )


async def test_wind_bearing_ozone_and_cloud_coverage_and_uv_index(
    hass: HomeAssistant,
    config_flow_fixture: None,
) -> None:
    """Test wind bearing, ozone and cloud coverage."""
    wind_bearing_value = 180
    ozone_value = 10
    cloud_coverage = 75
    uv_index = 1.2

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "wind_bearing": wind_bearing_value,
        "ozone": ozone_value,
        "cloud_coverage": cloud_coverage,
        "uv_index": uv_index,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]
    assert float(state.attributes[ATTR_WEATHER_WIND_BEARING]) == 180
    assert float(state.attributes[ATTR_WEATHER_OZONE]) == 10
    assert float(state.attributes[ATTR_WEATHER_CLOUD_COVERAGE]) == 75
    assert float(state.attributes[ATTR_WEATHER_UV_INDEX]) == 1.2
    assert float(forecast[ATTR_FORECAST_UV_INDEX]) == 1.2


async def test_humidity(
    hass: HomeAssistant,
    config_flow_fixture: None,
) -> None:
    """Test humidity."""
    humidity_value = 80.2

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {"humidity": humidity_value}

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]
    assert float(state.attributes[ATTR_WEATHER_HUMIDITY]) == 80
    assert float(forecast[ATTR_FORECAST_HUMIDITY]) == 80


async def test_none_forecast(
    hass: HomeAssistant,
    config_flow_fixture: None,
) -> None:
    """Test that conversion with None values succeeds."""

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_pressure": None,
        "native_pressure_unit": UnitOfPressure.INHG,
        "native_wind_speed": None,
        "native_wind_speed_unit": UnitOfSpeed.METERS_PER_SECOND,
        "native_precipitation": None,
        "native_precipitation_unit": UnitOfLength.MILLIMETERS,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    assert forecast.get(ATTR_FORECAST_PRESSURE) is None
    assert forecast.get(ATTR_FORECAST_WIND_SPEED) is None
    assert forecast.get(ATTR_FORECAST_PRECIPITATION) is None


async def test_custom_units(hass: HomeAssistant, config_flow_fixture: None) -> None:
    """Test custom unit."""
    wind_speed_value = 5
    wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    pressure_value = 110
    pressure_unit = UnitOfPressure.HPA
    temperature_value = 20
    temperature_unit = UnitOfTemperature.CELSIUS
    visibility_value = 11
    visibility_unit = UnitOfLength.KILOMETERS
    precipitation_value = 1.1
    precipitation_unit = UnitOfLength.MILLIMETERS

    set_options = {
        "wind_speed_unit": UnitOfSpeed.MILES_PER_HOUR,
        "precipitation_unit": UnitOfLength.INCHES,
        "pressure_unit": UnitOfPressure.INHG,
        "temperature_unit": UnitOfTemperature.FAHRENHEIT,
        "visibility_unit": UnitOfLength.MILES,
    }

    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get_or_create("weather", "test", "very_unique")
    entity_registry.async_update_entity_options(entry.entity_id, "weather", set_options)
    await hass.async_block_till_done()

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_temperature": temperature_value,
        "native_temperature_unit": temperature_unit,
        "native_wind_speed": wind_speed_value,
        "native_wind_speed_unit": wind_speed_unit,
        "native_pressure": pressure_value,
        "native_pressure_unit": pressure_unit,
        "native_visibility": visibility_value,
        "native_visibility_unit": visibility_unit,
        "native_precipitation": precipitation_value,
        "native_precipitation_unit": precipitation_unit,
        "is_daytime": True,
        "unique_id": "very_unique",
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected_wind_speed = round(
        SpeedConverter.convert(
            wind_speed_value, wind_speed_unit, UnitOfSpeed.MILES_PER_HOUR
        ),
        ROUNDING_PRECISION,
    )
    expected_temperature = TemperatureConverter.convert(
        temperature_value, temperature_unit, UnitOfTemperature.FAHRENHEIT
    )
    expected_pressure = round(
        PressureConverter.convert(pressure_value, pressure_unit, UnitOfPressure.INHG),
        ROUNDING_PRECISION,
    )
    expected_visibility = round(
        DistanceConverter.convert(
            visibility_value, visibility_unit, UnitOfLength.MILES
        ),
        ROUNDING_PRECISION,
    )
    expected_precipitation = round(
        DistanceConverter.convert(
            precipitation_value, precipitation_unit, UnitOfLength.INCHES
        ),
        ROUNDING_PRECISION,
    )

    assert float(state.attributes[ATTR_WEATHER_WIND_SPEED]) == pytest.approx(
        expected_wind_speed
    )
    assert float(state.attributes[ATTR_WEATHER_TEMPERATURE]) == pytest.approx(
        expected_temperature, rel=0.1
    )
    assert float(state.attributes[ATTR_WEATHER_PRESSURE]) == pytest.approx(
        expected_pressure
    )
    assert float(state.attributes[ATTR_WEATHER_VISIBILITY]) == pytest.approx(
        expected_visibility
    )
    assert float(forecast[ATTR_FORECAST_PRECIPITATION]) == pytest.approx(
        expected_precipitation, rel=1e-2
    )

    assert (
        state.attributes[ATTR_WEATHER_PRECIPITATION_UNIT]
        == set_options["precipitation_unit"]
    )
    assert state.attributes[ATTR_WEATHER_PRESSURE_UNIT] == set_options["pressure_unit"]
    assert (
        state.attributes[ATTR_WEATHER_TEMPERATURE_UNIT]
        == set_options["temperature_unit"]
    )
    assert (
        state.attributes[ATTR_WEATHER_VISIBILITY_UNIT] == set_options["visibility_unit"]
    )
    assert (
        state.attributes[ATTR_WEATHER_WIND_SPEED_UNIT] == set_options["wind_speed_unit"]
    )


async def test_backwards_compatibility_round_temperature(hass: HomeAssistant) -> None:
    """Test backward compatibility for rounding temperature."""

    assert round_temperature(20.3, PRECISION_HALVES) == 20.5
    assert round_temperature(20.3, PRECISION_TENTHS) == 20.3
    assert round_temperature(20.3, PRECISION_WHOLE) == 20
    assert round_temperature(None, PRECISION_WHOLE) is None


async def test_attr(hass: HomeAssistant) -> None:
    """Test the _attr attributes."""

    weather = MockWeatherEntity()
    weather.hass = hass

    assert weather.condition == ATTR_CONDITION_SUNNY
    assert weather.native_precipitation_unit == UnitOfLength.MILLIMETERS
    assert weather._precipitation_unit == UnitOfLength.MILLIMETERS
    assert weather.native_pressure == 10
    assert weather.native_pressure_unit == UnitOfPressure.HPA
    assert weather._pressure_unit == UnitOfPressure.HPA
    assert weather.native_temperature == 20
    assert weather.native_temperature_unit == UnitOfTemperature.CELSIUS
    assert weather._temperature_unit == UnitOfTemperature.CELSIUS
    assert weather.native_visibility == 30
    assert weather.native_visibility_unit == UnitOfLength.KILOMETERS
    assert weather._visibility_unit == UnitOfLength.KILOMETERS
    assert weather.native_wind_speed == 3
    assert weather.native_wind_speed_unit == UnitOfSpeed.METERS_PER_SECOND
    assert weather._wind_speed_unit == UnitOfSpeed.KILOMETERS_PER_HOUR


async def test_precision_for_temperature(
    hass: HomeAssistant,
    config_flow_fixture: None,
) -> None:
    """Test the precision for temperature."""

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

    kwargs = {
        "precision": PRECISION_HALVES,
        "native_temperature": 23.3,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
        "native_dew_point": 2.7,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    state = hass.states.get(entity0.entity_id)

    assert state.state == ATTR_CONDITION_SUNNY
    assert state.attributes[ATTR_WEATHER_TEMPERATURE] == 23.5
    assert state.attributes[ATTR_WEATHER_DEW_POINT] == 2.5
    assert state.attributes[ATTR_WEATHER_TEMPERATURE_UNIT] == UnitOfTemperature.CELSIUS


async def test_forecast_twice_daily_missing_is_daytime(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    config_flow_fixture: None,
) -> None:
    """Test forecast_twice_daily missing mandatory attribute is_daytime."""

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
        "is_daytime": None,
        "supported_features": WeatherEntityFeature.FORECAST_TWICE_DAILY,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "weather/subscribe_forecast",
            "forecast_type": "twice_daily",
            "entity_id": entity0.entity_id,
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] is None
    subscription_id = msg["id"]

    msg = await client.receive_json()
    assert msg["id"] == subscription_id
    assert msg["error"] == {"code": "unknown_error", "message": "Unknown error"}
    assert not msg["success"]
    assert msg["type"] == "result"


@pytest.mark.parametrize(
    ("service"),
    [
        SERVICE_GET_FORECASTS,
        LEGACY_SERVICE_GET_FORECAST,
    ],
)
@pytest.mark.parametrize(
    ("forecast_type", "supported_features"),
    [
        ("daily", WeatherEntityFeature.FORECAST_DAILY),
        ("hourly", WeatherEntityFeature.FORECAST_HOURLY),
        (
            "twice_daily",
            WeatherEntityFeature.FORECAST_TWICE_DAILY,
        ),
    ],
)
async def test_get_forecast(
    hass: HomeAssistant,
    config_flow_fixture: None,
    forecast_type: str,
    supported_features: int,
    snapshot: SnapshotAssertion,
    service: str,
) -> None:
    """Test get forecast service."""

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        async def async_forecast_daily(self) -> list[Forecast] | None:
            """Return the forecast_daily."""
            return self.forecast_list

        async def async_forecast_twice_daily(self) -> list[Forecast] | None:
            """Return the forecast_twice_daily."""
            forecast = self.forecast_list[0]
            forecast["is_daytime"] = True
            return [forecast]

        async def async_forecast_hourly(self) -> list[Forecast] | None:
            """Return the forecast_hourly."""
            return self.forecast_list

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
        "supported_features": supported_features,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    response = await hass.services.async_call(
        DOMAIN,
        service,
        {
            "entity_id": entity0.entity_id,
            "type": forecast_type,
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


@pytest.mark.parametrize(
    ("service", "expected"),
    [
        (
            SERVICE_GET_FORECASTS,
            {
                "weather.testing": {
                    "forecast": [],
                }
            },
        ),
        (
            LEGACY_SERVICE_GET_FORECAST,
            {
                "forecast": [],
            },
        ),
    ],
)
async def test_get_forecast_no_forecast(
    hass: HomeAssistant,
    config_flow_fixture: None,
    service: str,
    expected: dict[str, list | dict[str, list]],
) -> None:
    """Test get forecast service."""

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        async def async_forecast_daily(self) -> list[Forecast] | None:
            """Return the forecast_daily."""
            return None

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
        "supported_features": WeatherEntityFeature.FORECAST_DAILY,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    response = await hass.services.async_call(
        DOMAIN,
        service,
        {
            "entity_id": entity0.entity_id,
            "type": "daily",
        },
        blocking=True,
        return_response=True,
    )
    assert response == expected


@pytest.mark.parametrize(
    ("service"),
    [
        SERVICE_GET_FORECASTS,
        LEGACY_SERVICE_GET_FORECAST,
    ],
)
@pytest.mark.parametrize(
    ("supported_features", "forecast_types"),
    [
        (WeatherEntityFeature.FORECAST_DAILY, ["hourly", "twice_daily"]),
        (WeatherEntityFeature.FORECAST_HOURLY, ["daily", "twice_daily"]),
        (WeatherEntityFeature.FORECAST_TWICE_DAILY, ["daily", "hourly"]),
    ],
)
async def test_get_forecast_unsupported(
    hass: HomeAssistant,
    config_flow_fixture: None,
    forecast_types: list[str],
    supported_features: int,
    service: str,
) -> None:
    """Test get forecast service."""

    class MockWeatherMockForecast(MockWeatherTest):
        """Mock weather class with mocked legacy forecast."""

        async def async_forecast_daily(self) -> list[Forecast] | None:
            """Return the forecast_daily."""
            return self.forecast_list

        async def async_forecast_twice_daily(self) -> list[Forecast] | None:
            """Return the forecast_twice_daily."""
            return self.forecast_list

        async def async_forecast_hourly(self) -> list[Forecast] | None:
            """Return the forecast_hourly."""
            return self.forecast_list

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
        "supported_features": supported_features,
    }
    weather_entity = await create_entity(hass, MockWeatherMockForecast, None, **kwargs)

    for forecast_type in forecast_types:
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN,
                service,
                {
                    "entity_id": weather_entity.entity_id,
                    "type": forecast_type,
                },
                blocking=True,
                return_response=True,
            )


ISSUE_TRACKER = "https://blablabla.com"


@pytest.mark.parametrize(
    ("manifest_extra", "translation_key", "translation_placeholders_extra", "report"),
    [
        (
            {},
            "deprecated_weather_forecast_no_url",
            {},
            "report it to the author of the 'test' custom integration",
        ),
        (
            {"issue_tracker": ISSUE_TRACKER},
            "deprecated_weather_forecast_url",
            {"issue_tracker": ISSUE_TRACKER},
            "create a bug report at https://blablabla.com",
        ),
    ],
)
async def test_issue_forecast_property_deprecated(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    config_flow_fixture: None,
    manifest_extra: dict[str, str],
    translation_key: str,
    translation_placeholders_extra: dict[str, str],
    report: str,
) -> None:
    """Test the issue is raised on deprecated forecast attributes."""

    class MockWeatherMockLegacyForecastOnly(MockWeatherTest):
        """Mock weather class with mocked legacy forecast."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    # Fake that the class belongs to a custom integration
    MockWeatherMockLegacyForecastOnly.__module__ = "custom_components.test.weather"

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
    }
    weather_entity = await create_entity(
        hass, MockWeatherMockLegacyForecastOnly, manifest_extra, **kwargs
    )

    assert weather_entity.state == ATTR_CONDITION_SUNNY

    issues = ir.async_get(hass)
    issue = issues.async_get_issue("weather", "deprecated_weather_forecast_test")
    assert issue
    assert issue.issue_domain == "test"
    assert issue.issue_id == "deprecated_weather_forecast_test"
    assert issue.translation_key == translation_key
    assert (
        issue.translation_placeholders
        == {"platform": "test"} | translation_placeholders_extra
    )

    assert (
        "test::MockWeatherMockLegacyForecastOnly implements the `forecast` property or "
        "sets `self._attr_forecast` in a subclass of WeatherEntity, this is deprecated "
        f"and will be unsupported from Home Assistant 2024.3. Please {report}"
    ) in caplog.text


async def test_issue_forecast_attr_deprecated(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
    config_flow_fixture: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the issue is raised on deprecated forecast attributes."""

    class MockWeatherMockLegacyForecast(MockWeatherTest):
        """Mock weather class with legacy forecast."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
    }

    # Fake that the class belongs to a custom integration
    MockWeatherMockLegacyForecast.__module__ = "custom_components.test.weather"

    weather_entity = await create_entity(
        hass, MockWeatherMockLegacyForecast, None, **kwargs
    )

    assert weather_entity.state == ATTR_CONDITION_SUNNY

    issue = issue_registry.async_get_issue(
        "weather", "deprecated_weather_forecast_test"
    )
    assert issue
    assert issue.issue_domain == "test"
    assert issue.issue_id == "deprecated_weather_forecast_test"
    assert issue.translation_key == "deprecated_weather_forecast_no_url"
    assert issue.translation_placeholders == {"platform": "test"}

    assert (
        "test::MockWeatherMockLegacyForecast implements the `forecast` property or "
        "sets `self._attr_forecast` in a subclass of WeatherEntity, this is deprecated "
        "and will be unsupported from Home Assistant 2024.3. Please report it to the "
        "author of the 'test' custom integration"
    ) in caplog.text


async def test_issue_forecast_deprecated_no_logging(
    hass: HomeAssistant,
    config_flow_fixture: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the no issue is raised on deprecated forecast attributes if new methods exist."""

    class MockWeatherMockForecast(MockWeatherTest):
        """Mock weather class with mocked new method and legacy forecast."""

        @property
        def forecast(self) -> list[Forecast] | None:
            """Return the forecast."""
            return self.forecast_list

        async def async_forecast_daily(self) -> list[Forecast] | None:
            """Return the forecast_daily."""
            return self.forecast_list

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
    }

    weather_entity = await create_entity(hass, MockWeatherMockForecast, None, **kwargs)

    assert weather_entity.state == ATTR_CONDITION_SUNNY

    assert "Setting up weather.test" in caplog.text
    assert (
        "custom_components.test_weather.weather::weather.test is using a forecast attribute on an instance of WeatherEntity"
        not in caplog.text
    )


async def test_issue_deprecated_service_weather_get_forecast(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
    config_flow_fixture: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the issue is raised on deprecated service weather.get_forecast."""

    class MockWeatherMock(MockWeatherTest):
        """Mock weather class."""

        async def async_forecast_daily(self) -> list[Forecast] | None:
            """Return the forecast_daily."""
            return self.forecast_list

    kwargs = {
        "native_temperature": 38,
        "native_temperature_unit": UnitOfTemperature.CELSIUS,
        "supported_features": WeatherEntityFeature.FORECAST_DAILY,
    }

    entity0 = await create_entity(hass, MockWeatherMock, None, **kwargs)

    _ = await hass.services.async_call(
        DOMAIN,
        LEGACY_SERVICE_GET_FORECAST,
        {
            "entity_id": entity0.entity_id,
            "type": "daily",
        },
        blocking=True,
        return_response=True,
    )

    issue = issue_registry.async_get_issue(
        "weather", "deprecated_service_weather_get_forecast"
    )
    assert issue
    assert issue.issue_domain == "test"
    assert issue.issue_id == "deprecated_service_weather_get_forecast"
    assert issue.translation_key == "deprecated_service_weather_get_forecast"

    assert (
        "Detected use of service 'weather.get_forecast'. "
        "This is deprecated and will stop working in Home Assistant 2024.6. "
        "Use 'weather.get_forecasts' instead which supports multiple entities"
    ) in caplog.text
