"""CalDAV todo platform."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from functools import partial
import logging
from typing import cast

import caldav
from caldav.lib.error import DAVError, NotFoundError
import requests

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import async_get_calendars, get_attr_value
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=15)

SUPPORTED_COMPONENT = "VTODO"
TODO_STATUS_MAP = {
    "NEEDS-ACTION": TodoItemStatus.NEEDS_ACTION,
    "IN-PROCESS": TodoItemStatus.NEEDS_ACTION,
    "COMPLETED": TodoItemStatus.COMPLETED,
    "CANCELLED": TodoItemStatus.COMPLETED,
}
TODO_STATUS_MAP_INV: dict[TodoItemStatus, str] = {
    TodoItemStatus.NEEDS_ACTION: "NEEDS-ACTION",
    TodoItemStatus.COMPLETED: "COMPLETED",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CalDav todo platform for a config entry."""
    client: caldav.DAVClient = hass.data[DOMAIN][entry.entry_id]
    calendars = await async_get_calendars(hass, client, SUPPORTED_COMPONENT)
    async_add_entities(
        (
            WebDavTodoListEntity(
                calendar,
                entry.entry_id,
            )
            for calendar in calendars
        ),
        True,
    )


def _todo_item(resource: caldav.CalendarObjectResource) -> TodoItem | None:
    """Convert a caldav Todo into a TodoItem."""
    if (
        not hasattr(resource.instance, "vtodo")
        or not (todo := resource.instance.vtodo)
        or (uid := get_attr_value(todo, "uid")) is None
        or (summary := get_attr_value(todo, "summary")) is None
    ):
        return None
    return TodoItem(
        uid=uid,
        summary=summary,
        status=TODO_STATUS_MAP.get(
            get_attr_value(todo, "status") or "",
            TodoItemStatus.NEEDS_ACTION,
        ),
    )


class WebDavTodoListEntity(TodoListEntity):
    """CalDAV To-do list entity."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, calendar: caldav.Calendar, config_entry_id: str) -> None:
        """Initialize WebDavTodoListEntity."""
        self._calendar = calendar
        self._attr_name = (calendar.name or "Unknown").capitalize()
        self._attr_unique_id = f"{config_entry_id}-{calendar.id}"

    async def async_update(self) -> None:
        """Update To-do list entity state."""
        results = await self.hass.async_add_executor_job(
            partial(
                self._calendar.search,
                todo=True,
                include_completed=True,
            )
        )
        self._attr_todo_items = [
            todo_item
            for resource in results
            if (todo_item := _todo_item(resource)) is not None
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the To-do list."""
        try:
            await self.hass.async_add_executor_job(
                partial(
                    self._calendar.save_todo,
                    summary=item.summary,
                    status=TODO_STATUS_MAP_INV.get(
                        item.status or TodoItemStatus.NEEDS_ACTION, "NEEDS-ACTION"
                    ),
                ),
            )
        except (requests.ConnectionError, DAVError) as err:
            raise HomeAssistantError(f"CalDAV save error: {err}") from err

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a To-do item."""
        uid: str = cast(str, item.uid)
        try:
            todo = await self.hass.async_add_executor_job(
                self._calendar.todo_by_uid, uid
            )
        except NotFoundError as err:
            raise HomeAssistantError(f"Could not find To-do item {uid}") from err
        except (requests.ConnectionError, DAVError) as err:
            raise HomeAssistantError(f"CalDAV lookup error: {err}") from err
        vtodo = todo.icalendar_component  # type: ignore[attr-defined]
        if item.summary:
            vtodo["summary"] = item.summary
        if item.status:
            vtodo["status"] = TODO_STATUS_MAP_INV.get(item.status, "NEEDS-ACTION")
        try:
            await self.hass.async_add_executor_job(
                partial(
                    todo.save,
                    no_create=True,
                    obj_type="todo",
                ),
            )
        except (requests.ConnectionError, DAVError) as err:
            raise HomeAssistantError(f"CalDAV save error: {err}") from err

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete To-do items."""
        tasks = (
            self.hass.async_add_executor_job(self._calendar.todo_by_uid, uid)
            for uid in uids
        )

        try:
            items = await asyncio.gather(*tasks)
        except NotFoundError as err:
            raise HomeAssistantError("Could not find To-do item") from err
        except (requests.ConnectionError, DAVError) as err:
            raise HomeAssistantError(f"CalDAV lookup error: {err}") from err

        # Run serially as some CalDAV servers do not support concurrent modifications
        for item in items:
            try:
                await self.hass.async_add_executor_job(item.delete)
            except (requests.ConnectionError, DAVError) as err:
                raise HomeAssistantError(f"CalDAV delete error: {err}") from err
