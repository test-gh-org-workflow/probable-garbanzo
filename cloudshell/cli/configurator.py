#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from abc import ABCMeta, abstractmethod

from cloudshell.cli.service.cli import CLI
from cloudshell.cli.session.ssh_session import SSHSession
from cloudshell.cli.session.telnet_session import TelnetSession

ABC = ABCMeta("ABC", (object,), {"__slots__": ()})

if sys.version_info >= (3, 0):
    from functools import lru_cache
else:
    from functools32 import lru_cache


class CLIServiceConfigurator(object):
    REGISTERED_SESSIONS = (SSHSession, TelnetSession)

    def __init__(self, resource_config, logger, cli=None, registered_sessions=None):
        """Initialize CLI service configurator.

        :param cloudshell.shell.standards.resource_config_generic_models.GenericCLIConfig resource_config:  # noqa: E501
        :param logging.Logger logger:
        :param cloudshell.cli.service.cli.CLI cli:
        :param collections.Iterable registered_sessions: Registered session types and order,
        could be defined as a dict with initialize methods. Example:
        {SSHSession: self._initialize_ssh_session}.
        """
        self._cli = cli or CLI()
        self._resource_config = resource_config
        self._logger = logger
        self._registered_sessions = registered_sessions or self.REGISTERED_SESSIONS

    @property
    def _username(self):
        return self._resource_config.user

    @property
    @lru_cache()
    def _password(self):
        return self._resource_config.password

    @property
    @lru_cache()
    def _pkey(self):
        return self._resource_config.private_key

    @property
    def _resource_address(self):
        """Resource IP."""
        return self._resource_config.address

    @property
    def _port(self):
        """Connection port property, to open socket on."""
        return self._resource_config.cli_tcp_port

    @property
    def _cli_type(self):
        """Connection type property [ssh|telnet|console|auto]."""
        return self._resource_config.cli_connection_type

    @property
    @lru_cache()
    def _session_dict(self):
        return {sess.SESSION_TYPE.lower(): [sess] for sess in self._registered_sessions}

    def _on_session_start(self, session, logger):
        """Perform some default commands when session just opened.

        Like 'no logging console'
        """
        pass

    def _assign_initializers(self):
        pass

    def _initialize_session(self, session_class):
        return session_class(
            host=self._resource_address,
            username=self._username,
            password=self._password,
            port=self._port,
            on_session_start=self._on_session_start,
        )

    def _initialize_ssh_session_with_pkey(self, session_class):
        return session_class(
            host=self._resource_address,
            username=self._username,
            password=self._password,
            port=self._port,
            on_session_start=self._on_session_start,
            pkey=self._pkey,
        )

    def _defined_sessions(self):
        sessions = []
        for sess in self._session_dict.get(
            self._cli_type.lower(), self._registered_sessions
        ):
            if isinstance(self._registered_sessions, dict):
                session_initializer = (
                    self._registered_sessions.get(sess) or self._initialize_session
                )
            else:
                session_initializer = self._initialize_session
            sessions.append(session_initializer(sess))
        return sessions

    def get_cli_service(self, command_mode):
        """Use cli.get_session to open CLI connection and switch into required mode.

        :param CommandMode command_mode: operation mode, can be
            default_mode/enable_mode/config_mode/etc.
        :return: created session in provided mode
        :rtype: cloudshell.cli.service.session_pool_context_manager.SessionPoolContextManager  # noqa: E501
        """
        return self._cli.get_session(
            self._defined_sessions(), command_mode, self._logger
        )


class AbstractModeConfigurator(ABC, CLIServiceConfigurator):
    """Used by shells to run enable/config command."""

    @property
    @abstractmethod
    def enable_mode(self):
        pass

    @property
    @abstractmethod
    def config_mode(self):
        pass

    def enable_mode_service(self):
        return self.get_cli_service(self.enable_mode)

    def config_mode_service(self):
        return self.get_cli_service(self.config_mode)
