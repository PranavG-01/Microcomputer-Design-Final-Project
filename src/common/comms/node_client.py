from __future__ import annotations

import socket
import threading
import time
from typing import Callable, Optional

from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf

from .protocol import AlarmEvent, EventType


class _ServiceListener:
	def __init__(self, parent: "AlarmNode") -> None:
		self.parent = parent

	def add_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
		info = zeroconf.get_service_info(service_type, name)
		if info:
			self.parent._on_service_found(info)

	def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
		# if the removed service is the one we're connected to, disconnect
		self.parent._on_service_removed(name)


class AlarmNode:
	"""Node side that discovers the host via mDNS and connects to it.

	- Discovers a service of type `_alarmmesh._tcp.local.` and connects to the
	  first host that appears.
	- Sends `AlarmEvent` messages to the host over TCP (newline-delimited JSON).
	- Receives events from the host and calls `on_event`.
	- Sends periodic heartbeats and disconnects if host does not respond.
	"""

	def __init__(
		self,
		name: str,
		service_type: str = "_alarmmesh._tcp.local.",
		heartbeat_interval: float = 5.0,
		heartbeat_timeout: float = 15.0,
	) -> None:
		self.name = name
		self.service_type = service_type
		self.heartbeat_interval = heartbeat_interval
		self.heartbeat_timeout = heartbeat_timeout

		self._zeroconf = Zeroconf()
		self._browser = ServiceBrowser(self._zeroconf, self.service_type, _ServiceListener(self))

		self._sock: Optional[socket.socket] = None
		self._recv_thread: Optional[threading.Thread] = None
		self._hb_thread: Optional[threading.Thread] = None
		self._last_seen = 0.0
		self._running = False

		self.on_event: Callable[[AlarmEvent], None] | None = None

		# resolved service name we're connected to (or None)
		self._connected_service_name: Optional[str] = None

	def start(self) -> None:
		self._running = True
		# browser is already started by creation; threads start when service found

	def stop(self) -> None:
		self._running = False
		try:
			if self._sock:
				self._sock.close()
		except Exception:
			pass
		try:
			self._zeroconf.close()
		except Exception:
			pass

	def send(self, event: AlarmEvent) -> None:
		if not self._sock:
			return
		try:
			self._sock.sendall((event.to_json() + "\n").encode())
		except Exception:
			self._disconnect()

	def _on_service_found(self, info: ServiceInfo) -> None:
		if not self._running:
			return
		# if already connected, ignore new services
		if self._sock:
			return
		addresses = info.addresses
		if not addresses:
			return
		ip = socket.inet_ntoa(addresses[0])
		port = info.port
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(5.0)
			sock.connect((ip, port))
			sock.settimeout(None)
		except Exception:
			return

		self._sock = sock
		self._connected_service_name = info.name
		self._last_seen = time.time()
		self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
		self._recv_thread.start()
		self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
		self._hb_thread.start()

	def _on_service_removed(self, name: str) -> None:
		if self._connected_service_name and name == self._connected_service_name:
			self._disconnect()

	def _recv_loop(self) -> None:
		try:
			f = self._sock.makefile("r")
			while self._running and self._sock:
				line = f.readline()
				if not line:
					break
				line = line.strip()
				if not line:
					continue
				try:
					evt = AlarmEvent.from_json(line)
				except Exception:
					continue
				# update last seen for heartbeat responses
				if evt.type == EventType.HEARTBEAT:
					self._last_seen = time.time()
				if self.on_event:
					try:
						self.on_event(evt)
					except Exception:
						pass
		finally:
			self._disconnect()

	def _heartbeat_loop(self) -> None:
		while self._running and self._sock:
			# send heartbeat
			try:
				self._sock.sendall((AlarmEvent(type=EventType.HEARTBEAT).to_json() + "\n").encode())
			except Exception:
				self._disconnect()
				break
			# sleep and then check last_seen
			time.sleep(self.heartbeat_interval)
			if time.time() - self._last_seen > self.heartbeat_timeout:
				# no heartbeat response from host in time
				self._disconnect()
				break

	def _disconnect(self) -> None:
		try:
			if self._sock:
				try:
					self._sock.shutdown(socket.SHUT_RDWR)
				except Exception:
					pass
				self._sock.close()
		finally:
			self._sock = None
			self._connected_service_name = None

