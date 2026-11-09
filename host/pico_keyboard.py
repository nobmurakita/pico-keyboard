"""pico-keyboard ホスト側ライブラリ / CLI

ライブラリとして:
    from pico_keyboard import PicoKeyboard
    with PicoKeyboard() as kb:          # ポート自動検出 (port="COM5" で指定も可)
        kb.layout("jp")
        kb.type("user@example.com")
        kb.key("tab")
        kb.type("password")
        kb.key("enter")

CLI として:
    python pico_keyboard.py -t "user" -k tab -t "pass" -k enter
    python pico_keyboard.py -f input.txt
    echo hello | python pico_keyboard.py -f -
"""

import argparse
import sys
import time

import serial
from serial.tools import list_ports

CIRCUITPY_VID = 0x239A
CHUNK = 128  # 1 コマンドで送る最大文字数


class PicoKeyboardError(Exception):
    pass


class PicoKeyboard:
    def __init__(self, port=None, baudrate=115200, delay_ms=None, layout=None):
        self.port = port or find_port()
        self.ser = serial.Serial(self.port, baudrate, timeout=0.2)
        self.ser.reset_input_buffer()
        self._delay = 0.01
        self.ping()
        if layout:
            self.layout(layout)
        if delay_ms is not None:
            self.delay(delay_ms)

    # --- 低レベル ---
    def command(self, line, timeout=5.0):
        if "\n" in line or "\r" in line:
            raise ValueError("command must be a single line")
        self.ser.write((line + "\n").encode("utf-8"))
        self.ser.flush()
        return self._read_reply(timeout)

    def _read_reply(self, timeout):
        deadline = time.monotonic() + timeout
        buf = b""
        while time.monotonic() < deadline:
            buf += self.ser.read(self.ser.in_waiting or 1)
            if b"\n" in buf:
                reply = buf.split(b"\n", 1)[0].decode("utf-8", "replace").strip()
                if reply.startswith("OK"):
                    return reply
                raise PicoKeyboardError(reply)
        raise PicoKeyboardError("timeout waiting for reply")

    # --- 高レベル ---
    def ping(self):
        return self.command("P", timeout=2.0)

    def layout(self, name):
        self.command("L " + name)

    def delay(self, ms):
        self._delay = ms / 1000
        self.command("D %d" % ms)

    def wait(self, ms):
        self.command("W %d" % ms, timeout=ms / 1000 + 5)

    def release_all(self):
        self.command("R")

    def key(self, *combos):
        """例: key("ctrl+alt+delete"), key("tab", "tab", "enter")"""
        for c in combos:
            self.command("K " + c, timeout=self._timeout(1))

    def type(self, text):
        """テキストを入力する。改行は Enter として送る。"""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        for i, line in enumerate(lines):
            for j in range(0, len(line), CHUNK):
                chunk = line[j:j + CHUNK]
                self.command("T " + chunk, timeout=self._timeout(len(chunk)))
            if i < len(lines) - 1:
                self.key("enter")

    def _timeout(self, n):
        # 1 文字あたり最大 4 回 sleep する
        return 5.0 + n * 4 * self._delay * 1.5

    def close(self):
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def find_port():
    """CircuitPython の CDC ポートに P を送り、応答したポートを返す"""
    candidates = [p.device for p in list_ports.comports() if p.vid == CIRCUITPY_VID]
    for dev in candidates:
        try:
            with serial.Serial(dev, 115200, timeout=0.3) as s:
                s.reset_input_buffer()
                s.write(b"P\n")
                deadline = time.monotonic() + 1.0
                buf = b""
                while time.monotonic() < deadline and b"\n" not in buf:
                    buf += s.read(64)
                if b"OK pico-keyboard" in buf:
                    return dev
        except serial.SerialException:
            continue
    raise PicoKeyboardError(
        "pico-keyboard not found (candidates: %s). Use --port." % (candidates or "none"))


class _Ordered(argparse.Action):
    """-t/-k/-w/-f をコマンドライン上の順序どおりに記録する"""

    def __call__(self, parser, ns, values, option_string=None):
        if getattr(ns, "actions", None) is None:
            ns.actions = []
        ns.actions.append((self.dest, values))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pico-keyboard", description="Send keystrokes via pico-keyboard")
    ap.add_argument("-p", "--port", help="シリアルポート (省略時は自動検出)")
    ap.add_argument("-l", "--layout", choices=["us", "jp"], help="ホスト側キーボードレイアウト")
    ap.add_argument("-d", "--delay", type=int, help="キー押下時間/間隔 (ms)")
    ap.add_argument("-t", "--text", dest="text", action=_Ordered, help="テキストを入力")
    ap.add_argument("-k", "--key", dest="key", action=_Ordered,
                    help="キーを押す (例: enter, ctrl+alt+delete, win+r)")
    ap.add_argument("-w", "--wait", dest="wait", type=int, action=_Ordered, help="待機 (ms)")
    ap.add_argument("-f", "--file", dest="file", action=_Ordered,
                    help="ファイルの内容を入力 ('-' で標準入力)")
    ap.add_argument("--list", action="store_true", help="候補ポートを表示して終了")
    args = ap.parse_args(argv)

    if args.list:
        for p in list_ports.comports():
            print(p.device, hex(p.vid or 0), p.description)
        return 0

    actions = getattr(args, "actions", None) or []
    if not actions:
        ap.error("nothing to do (use -t / -k / -w / -f)")

    try:
        with PicoKeyboard(args.port, delay_ms=args.delay, layout=args.layout) as kb:
            for kind, value in actions:
                if kind == "text":
                    kb.type(value)
                elif kind == "key":
                    kb.key(*value.split())
                elif kind == "wait":
                    kb.wait(value)
                elif kind == "file":
                    if value == "-":
                        data = sys.stdin.read()
                    else:
                        with open(value, encoding="utf-8") as f:
                            data = f.read()
                    kb.type(data)
    except (PicoKeyboardError, serial.SerialException) as e:
        print("error:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
