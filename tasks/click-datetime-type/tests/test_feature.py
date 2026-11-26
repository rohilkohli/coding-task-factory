"""Hidden feature tests for the click DateTime parameter type task.

The first four tests are the upstream tests removed from the agent's copy of
the repository (pallets/click @ 08b803c). The remaining tests pin down each
behaviour stated in instruction.md so that partial implementations fail.
"""

from __future__ import annotations

from datetime import datetime

import pytest

import click
from click.testing import CliRunner

DEFAULT_FORMATS = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]


@pytest.fixture
def runner():
    return CliRunner()


def _echo_cli(type_):
    @click.command()
    @click.option("--start_date", type=type_)
    def cli(start_date):
        click.echo(start_date.strftime("%Y-%m-%dT%H:%M:%S"))

    return cli


# --- upstream tests (tests/test_basic.py, tests/test_info_dict.py) ---------


def test_datetime_argument_optional_metavar(runner):
    @click.command()
    @click.argument("when", type=click.DateTime(formats=["%Y-%m-%d"]), required=False)
    def cli(when):
        pass

    result = runner.invoke(cli, ["--help"])
    assert "Usage: cli [OPTIONS] [%Y-%m-%d]\n" in result.output
    assert "[[%Y-%m-%d]]" not in result.output


def test_datetime_option_default(runner):
    cli = _echo_cli(click.DateTime())

    result = runner.invoke(cli, ["--start_date=2015-09-29"])
    assert not result.exception
    assert result.output == "2015-09-29T00:00:00\n"

    result = runner.invoke(cli, ["--start_date=2015-09-29T09:11:22"])
    assert not result.exception
    assert result.output == "2015-09-29T09:11:22\n"

    result = runner.invoke(cli, ["--start_date=2015-09"])
    assert result.exit_code == 2
    assert (
        "Invalid value for '--start_date': '2015-09' does not match the formats"
        " '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'."
    ) in result.output

    result = runner.invoke(cli, ["--help"])
    assert (
        "--start_date [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]" in result.output
    )


def test_datetime_option_custom(runner):
    cli = _echo_cli(click.DateTime(formats=["%A %B %d, %Y"]))
    result = runner.invoke(cli, ["--start_date=Wednesday June 05, 2010"])
    assert not result.exception
    assert result.output == "2010-06-05T00:00:00\n"


def test_datetime_info_dict():
    assert click.DateTime(["%Y-%m-%d"]).to_info_dict() == {
        "param_type": "DateTime",
        "name": "datetime",
        "formats": ["%Y-%m-%d"],
    }


# --- additional behaviour checks ------------------------------------------


def test_exported_from_package_and_types_module():
    from click.types import DateTime

    assert click.DateTime is DateTime
    assert issubclass(DateTime, click.ParamType)


def test_default_formats_in_order():
    assert list(click.DateTime().formats) == DEFAULT_FORMATS


def test_custom_formats_are_stored():
    formats = ["%d.%m.%Y", "%Y/%m/%d"]
    assert list(click.DateTime(formats).formats) == formats


def test_space_separated_default_format(runner):
    result = runner.invoke(
        _echo_cli(click.DateTime()), ["--start_date", "2015-09-29 09:11:22"]
    )
    assert not result.exception
    assert result.output == "2015-09-29T09:11:22\n"


def test_returns_datetime_instances():
    value = click.DateTime().convert("2021-02-03", None, None)
    assert type(value) is datetime
    assert value == datetime(2021, 2, 3)


def test_first_matching_format_wins():
    # "2020-05-06" is valid for both formats; the first one listed must be used.
    value = click.DateTime(["%Y-%d-%m", "%Y-%m-%d"]).convert("2020-05-06", None, None)
    assert value == datetime(2020, 6, 5)


def test_later_format_used_when_earlier_ones_fail():
    value = click.DateTime(["%d.%m.%Y", "%Y/%m/%d"]).convert("2020/05/06", None, None)
    assert value == datetime(2020, 5, 6)


def test_datetime_value_passes_through_unchanged():
    original = datetime(1999, 12, 31, 23, 59, 59)
    assert click.DateTime(["%Y"]).convert(original, None, None) is original


def test_datetime_default_value(runner):
    @click.command()
    @click.option("--when", type=click.DateTime(), default=datetime(2001, 1, 2, 3, 4, 5))
    def cli(when):
        click.echo(when.isoformat())

    result = runner.invoke(cli, [])
    assert not result.exception
    assert result.output == "2001-01-02T03:04:05\n"


def test_single_format_error_uses_singular_wording(runner):
    result = runner.invoke(_echo_cli(click.DateTime(["%Y"])), ["--start_date", "abc"])
    assert result.exit_code == 2
    assert "'abc' does not match the format '%Y'." in result.output
    assert "formats" not in result.output.split("Invalid value", 1)[1]


def test_invalid_value_raises_bad_parameter():
    with pytest.raises(click.BadParameter) as exc:
        click.DateTime(["%Y-%m-%d", "%d/%m/%Y"]).convert("nope", None, None)
    assert str(exc.value.message) == (
        "'nope' does not match the formats '%Y-%m-%d', '%d/%m/%Y'."
    )


def test_custom_metavar_in_help(runner):
    @click.command()
    @click.option("--day", type=click.DateTime(["%d.%m.%Y", "%Y"]))
    def cli(day):
        pass

    result = runner.invoke(cli, ["--help"])
    assert "--day [%d.%m.%Y|%Y]" in result.output


def test_name_and_repr():
    dt = click.DateTime()
    assert dt.name == "datetime"
    assert repr(dt) == "DateTime"
