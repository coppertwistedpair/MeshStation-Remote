import queue
import threading

import pmt
import zmq
from gnuradio import gr


class PDUZMQSink(gr.basic_block):
    """Message sink that PUBs incoming PDUs (0x03 frames) over ZMQ.

    Binds a ZMQ PUB socket on host:port. MeshStation's External mode
    connects a ZMQ SUB socket to this address and expects the same
    0x03 framed byte stream the internal engine produces over TCP.
    """

    def __init__(self, host: str, port: int, out_queue: queue.Queue):
        gr.basic_block.__init__(self, name="PDUZMQSink", in_sig=None, out_sig=None)
        self._q = out_queue
        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self._handle)

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(host, port), daemon=True)
        self._thread.start()

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
