"""Tests for the preferences CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from rich.console import Console
from rich.table import Table

from omym.application.services.preferences_service import ArtistPreferenceRow
from omym.platform.db.db_manager import DatabaseManager
from omym.ui.cli.args.options import PreferencesArgs
from omym.ui.cli.commands.preferences import PreferencesCommand


def test_execute_renders_table(mocker: MockerFixture) -> None:
    args = PreferencesArgs(command="preferences", show_all=True, only_missing=False)
    rows = [
        ArtistPreferenceRow(
            artist_name="宇多田ヒカル",
            preferred_name="Utada Hikaru",
            cached_name="Utada Hikaru",
            source="musicbrainz",
        ),
        ArtistPreferenceRow(
            artist_name="東京事変",
            preferred_name=None,
            cached_name="Tokyo Incidents",
            source="manual",
        ),
    ]

    inspector = mocker.Mock()
    inspector.collect.return_value = rows

    console_mock: MagicMock = mocker.create_autospec(Console, instance=True)

    manager_mock = mocker.create_autospec(DatabaseManager, instance=True)
    manager_mock.__enter__.return_value = manager_mock
    manager_mock.__exit__.return_value = None
    manager_mock.conn = mocker.Mock()
    db_factory = lambda: manager_mock

    command = PreferencesCommand(
        args,
        db_manager_factory=db_factory,
        inspector_factory=lambda dao: inspector,
        console=console_mock,
    )

    command.execute()

    inspector.collect.assert_called_once_with(include_all=True)
    print_mock: MagicMock = console_mock.print
    print_mock.assert_called_once()
    rendered = print_mock.call_args[0][0]
    assert isinstance(rendered, Table)
    assert rendered.row_count == len(rows)


@pytest.mark.parametrize(
    "show_all, only_missing, expected_message",
    [
        (False, True, "No missing artist preferences detected."),
        (True, False, "No artist preference data available."),
    ],
)
def test_execute_handles_empty_rows(
    show_all: bool,
    only_missing: bool,
    expected_message: str,
    mocker: MockerFixture,
) -> None:
    args = PreferencesArgs(command="preferences", show_all=show_all, only_missing=only_missing)
    inspector = mocker.Mock()
    inspector.collect.return_value = []
    console_mock: MagicMock = mocker.create_autospec(Console, instance=True)
    manager_mock = mocker.create_autospec(DatabaseManager, instance=True)
    manager_mock.__enter__.return_value = manager_mock
    manager_mock.__exit__.return_value = None
    manager_mock.conn = mocker.Mock()
    db_factory = lambda: manager_mock

    command = PreferencesCommand(
        args,
        db_manager_factory=db_factory,
        inspector_factory=lambda dao: inspector,
        console=console_mock,
    )

    command.execute()

    inspector.collect.assert_called_once_with(include_all=show_all)
    print_mock: MagicMock = console_mock.print
    print_mock.assert_called_once()
    printed_arg = print_mock.call_args[0][0]
    assert expected_message in str(printed_arg)
