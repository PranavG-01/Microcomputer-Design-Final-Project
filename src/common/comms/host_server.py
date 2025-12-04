from __future__ import annotations

import socket
import threading
import time
from typing import Callable, Dict, Tuple

from zeroconf import ServiceInfo, Zeroconf

from .protocol import AlarmEvent, EventType


class AlarmHost:
	"""Host side of the alarm mesh.

	- Publishes an mDNS service so nodes can discover the host.
	- Accepts TCP connections from nodes.
	- Receives `AlarmEvent` messages from nodes and calls `on_event`.
	- Can broadcast `AlarmEvent` messages to all connected nodes.
	- Monitors heartbeats and disconnects clients after `heartbeat_timeout` seconds
	  of inactivity.
	"""

	def __init__(
		self,
		name: str,
		host: str = "0.0.0.0",
		port: int = 0,
		service_type: str = "_alarmmesh._tcp.local.",
		heartbeat_interval: float = 5.0,
		heartbeat_timeout: float = 15.0,
	) -> None:
		self.name = name
		self.host = host
		self.port = port
		self.service_type = service_type
		self.heartbeat_interval = heartbeat_interval
		self.heartbeat_timeout = heartbeat_timeout

		self._zeroconf = Zeroconf()
		self._service_info: ServiceInfo | None = None

		self._server_sock: socket.socket | None = None
		self._accept_thread: threading.Thread | None = None
		self._hb_thread: threading.Thread | None = None

		# clients: peer_addr_str -> (socket, last_seen, thread)
		self._clients: Dict[str, Tuple[socket.socket, float, threading.Thread]] = {}
		self._lock = threading.Lock()
		self._running = False

		# user-provided callback: Callable[[AlarmEvent, str], None]
		self.on_event: Callable[[AlarmEvent, str], None] | None = None

	def start(self) -> None:
		"""Start TCP server and publish mDNS service."""
		self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._server_sock.bind((self.host, self.port))
		self._server_sock.listen(5)
		bound_host, bound_port = self._server_sock.getsockname()
		self.port = bound_port

		# publish service
		addr = socket.inet_aton(socket.gethostbyname(socket.gethostname()))
		name = f"{self.name}.{self.service_type}"
		info = ServiceInfo(
			self.service_type,
			name,
			addresses=[addr],
			port=self.port,
			properties={},
			server=socket.gethostname() + ".",
		)
		self._service_info = info
		self._zeroconf.register_service(info)

		self._running = True
		self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
		self._accept_thread.start()

		self._hb_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
		self._hb_thread.start()

	def stop(self) -> None:
		"""Stop accepting new connections and unregister mDNS service."""
		self._running = False
		if self._server_sock:
			try:
				self._server_sock.close()
			except Exception:
				pass

		if self._service_info:
			try:
				self._zeroconf.unregister_service(self._service_info)
			except Exception:
				pass
		try:
			self._zeroconf.close()
		except Exception:
			pass

		# close clients
		with self._lock:
			for peer, (sock, _, thr) in list(self._clients.items()):
				try:
					sock.close()
				except Exception:
					pass
			self._clients.clear()

	def broadcast(self, event: AlarmEvent) -> None:
		"""Send an event to all connected nodes."""
		payload = event.to_json() + "\n"
		data = payload.encode()
		with self._lock:
			for peer, (sock, _, _) in list(self._clients.items()):
				try:
					sock.sendall(data)
				except Exception:
					# on send failure, remove client
					self._remove_client(peer)

	def _accept_loop(self) -> None:
		while self._running and self._server_sock:
			try:
				conn, addr = self._server_sock.accept()
			except Exception:
				break
			peer = f"{addr[0]}:{addr[1]}"
			thr = threading.Thread(target=self._handle_client, args=(conn, peer), daemon=True)
			with self._lock:
				self._clients[peer] = (conn, time.time(), thr)
			thr.start()

	def _handle_client(self, conn: socket.socket, peer: str) -> None:
		try:
			f = conn.makefile("r")
			while self._running:
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
				# update last seen
				with self._lock:
					if peer in self._clients:
						sock, _, thr = self._clients[peer]
						self._clients[peer] = (sock, time.time(), thr)

				# if heartbeat, respond with heartbeat (acts as a heartbeat ACK)
				if evt.type == EventType.HEARTBEAT:
					try:
						conn.sendall((AlarmEvent(type=EventType.HEARTBEAT).to_json() + "\n").encode())
					except Exception:
						pass

				# user callback
				if self.on_event:
					try:
						self.on_event(evt, peer)
					except Exception:
						pass
		finally:
			self._remove_client(peer)

	def _remove_client(self, peer: str) -> None:
		with self._lock:
			tup = self._clients.pop(peer, None)
		if tup:
			sock, _, _ = tup
			try:
				sock.close()
			except Exception:
				pass

	def _heartbeat_monitor(self) -> None:
		while self._running:
			now = time.time()
			to_remove = []
			with self._lock:
				for peer, (sock, last_seen, thr) in list(self._clients.items()):
					if now - last_seen > self.heartbeat_timeout:
						to_remove.append(peer)
			for peer in to_remove:
				self._remove_client(peer)
			time.sleep(max(0.5, self.heartbeat_interval))

