import queue
import threading
import time

import pmt
import zmq
from gnuradio import gr

HEARTBEAT_INTERVAL_S = 5.0


class PDUZMQSink(gr.basic_block):
    """Message sink that PUBs incoming PDUs (0x03 frames) over ZMQ.

    Binds a ZMQ PUB socket on host:port. MeshStation's External mode
    connects a ZMQ SUB socket to this address and expects the same
    0x03 framed byte stream the internal engine produces over TCP.

    Also logs proof-of-life to the console: an immediate line for every
    LoRa packet actually decoded (with SNR/RSSI), and a periodic heartbeat
    even when nothing has been heard, so a running-but-idle receiver
    doesn't look identical to a hung one.
    """

    def __init__(self, host: str, port: int, out_queue: queue.Queue):
        gr.basic_block.__init__(self, name="PDUZMQSink", in_sig=None, out_sig=None)
        self._q = out_queue
        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self._handle)

        self._stats_lock = threading.Lock()
        self._start_ts = time.monotonic()
        self._packet_count = 0
        self._last_packet_ts = None

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(host, port), daemon=True)
        self._thread.start()
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._hb_thread.start()

    @staticmethod
    def _parse_frame(data: bytes):
        # Mirrors the aggregator's _emit_unified() layout:
        # [0x03][len_hi][len_lo][pl_hi][pl_lo][payload...][flags][snr_i16][rssi_i16][preset_id]
        try:
            if len(data) < 3 or data[0] != 0x03:
                return None
            body = data[3:]
            if len(body) < 2:
                return None
            pl = (body[0] << 8) | body[1]
            tail_start = 2 + pl
            if len(body) < tail_start + 1 + 2 + 2 + 1:
                return None
            flags = body[tail_start]
            has_metrics = bool(flags & 0x01)
            snr = rssi = None
            if has_metrics:
                snr_raw = int.from_bytes(body[tail_start + 1:tail_start + 3], "big", signed=True)
                rssi_raw = int.from_bytes(body[tail_start + 3:tail_start + 5], "big", signed=True)
                snr, rssi = snr_raw / 10.0, rssi_raw / 10.0
            return {"payload_len": pl, "snr": snr, "rssi": rssi}
        except Exception:
            return None

    def _handle(self, msg) -> None:
        # Expect PDU: (meta . u8vector)
        if not pmt.is_pair(msg):
            return
        v = pmt.cdr(msg)
        if not pmt.is_u8vector(v):
            return

        data = bytes(bytearray(pmt.u8vector_elements(v)))

        # Non-blocking drop if queue is full
        try:
            self._q.put_nowait(data)
        except queue.Full:
            pass

        with self._stats_lock:
            self._packet_count += 1
            count = self._packet_count
            self._last_packet_ts = time.monotonic()

        info = self._parse_frame(data)
        if info and info["snr"] is not None:
            print(f"[MESHRX] packet #{count}: {info['payload_len']}B payload, "
                  f"SNR={info['snr']:.1f}dB RSSI={info['rssi']:.1f}dBm", flush=True)
        elif info:
            print(f"[MESHRX] packet #{count}: {info['payload_len']}B payload (no signal metrics)", flush=True)
        else:
            print(f"[MESHRX] packet #{count}: {len(data)}B frame", flush=True)

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(HEARTBEAT_INTERVAL_S):
            with self._stats_lock:
                count = self._packet_count
                last = self._last_packet_ts
            uptime = int(time.monotonic() - self._start_ts)
            since = "none yet" if last is None else f"{int(time.monotonic() - last)}s ago"
            print(f"[MESHRX] alive — uptime={uptime}s packets_heard={count} last_packet={since}", flush=True)

    def _run(self, host: str, port: int) -> None:
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind(f"tcp://{host}:{port}")

        while not self._stop.is_set():
            try:
                frame = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                socket.send(frame)
            except Exception:
                pass

        socket.close(linger=0)
        context.term()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._hb_thread:
            self._hb_thread.join(timeout=1.0)
