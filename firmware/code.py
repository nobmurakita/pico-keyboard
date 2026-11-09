# シリアルで受け取ったコマンドを USB キーボード入力として送出する
#
# プロトコル: 1 行 1 コマンド (UTF-8, 改行 LF)。各コマンドに "OK" または "ERR <理由>" を返す。
#   T <text>        テキストを入力 (行末までそのまま。先頭の空白 1 つだけ区切りとして除去)
#   K <combo> ...   キー/組み合わせを順に押す   例: K ctrl+alt+delete / K tab tab enter
#   W <ms>          待機
#   L <us|jp>       ホスト側キーボードレイアウトを設定 (既定: DEFAULT_LAYOUT)
#   D <ms>          キー押下時間と間隔を設定 (既定: DEFAULT_DELAY_MS)
#   P               疎通確認 ("OK pico-keyboard" を返す)
#   R               全キーを離す

import time
import usb_cdc
import usb_hid

import keymap

DEFAULT_LAYOUT = "us"
DEFAULT_DELAY_MS = 10
MAX_LINE = 4096


def find_keyboard():
    for d in usb_hid.devices:
        if d.usage_page == 0x01 and d.usage == 0x06:
            return d
    raise RuntimeError("keyboard HID device not found (boot.py is not applied?)")


class Keyboard:
    def __init__(self):
        self.dev = find_keyboard()
        self.report = bytearray(8)
        self.layout = keymap.LAYOUTS[DEFAULT_LAYOUT]
        self.delay = DEFAULT_DELAY_MS / 1000

    def _send(self, mod, key):
        self.report[0] = mod
        self.report[2] = key
        self.dev.send_report(self.report)

    def tap(self, mod, key):
        # 修飾キーを先に押してから本キーを押す (一部の環境で取りこぼし防止)
        if mod:
            self._send(mod, 0)
            time.sleep(self.delay)
        self._send(mod, key)
        time.sleep(self.delay)
        self._send(mod, 0)
        if mod:
            time.sleep(self.delay)
            self._send(0, 0)
        time.sleep(self.delay)

    def release_all(self):
        self._send(0, 0)

    def type_text(self, text):
        # 先に全文字を検証し、途中まで入力されて止まることを防ぐ
        seq = []
        for ch in text:
            if ch not in self.layout:
                raise ValueError("unsupported char: U+%04X" % ord(ch))
            seq.append(self.layout[ch])
        for code, mod in seq:
            self.tap(mod, code)

    def press_combos(self, combos):
        seq = [keymap.parse_combo(c, self.layout) for c in combos]
        for mod, key in seq:
            self.tap(mod, key)


def handle(kb, line):
    if not line:
        return "OK"
    cmd = line[0].upper()
    arg = line[2:] if len(line) > 1 and line[1] == " " else line[1:]
    if cmd == "T":
        kb.type_text(arg)
    elif cmd == "K":
        combos = arg.split()
        if not combos:
            raise ValueError("no key")
        kb.press_combos(combos)
    elif cmd == "W":
        time.sleep(int(arg) / 1000)
    elif cmd == "L":
        name = arg.strip().lower()
        if name not in keymap.LAYOUTS:
            raise ValueError("unknown layout: " + name)
        kb.layout = keymap.LAYOUTS[name]
    elif cmd == "D":
        kb.delay = max(0, int(arg)) / 1000
    elif cmd == "P":
        return "OK pico-keyboard"
    elif cmd == "R":
        kb.release_all()
    else:
        raise ValueError("unknown command: " + cmd)
    return "OK"


class Port:
    def __init__(self, stream):
        self.stream = stream
        self.buf = b""

    def poll(self):
        """完了した行のリストを返す"""
        n = self.stream.in_waiting
        if not n:
            return ()
        data = self.stream.read(n)
        if not data:
            return ()
        self.buf += data
        lines = []
        while True:
            i = self.buf.find(b"\n")
            if i < 0:
                break
            raw = self.buf[:i]
            self.buf = self.buf[i + 1:]
            if raw.endswith(b"\r"):
                raw = raw[:-1]
            lines.append(raw)
        if len(self.buf) > MAX_LINE:
            self.buf = b""
            lines.append(None)  # 行が長すぎる
        return lines

    def reply(self, msg):
        self.stream.write((msg + "\n").encode())


def main():
    kb = Keyboard()
    kb.release_all()

    if usb_cdc.data is None:
        raise RuntimeError("usb_cdc.data is disabled. Check boot.py and reset the board.")
    usb_cdc.data.timeout = 0
    port = Port(usb_cdc.data)

    print("pico-keyboard ready")
    while True:
        for raw in port.poll():
            if raw is None:
                port.reply("ERR line too long")
                continue
            try:
                msg = handle(kb, raw.decode("utf-8"))
            except Exception as e:  # noqa
                kb.release_all()
                msg = "ERR " + str(e)
            port.reply(msg)
        time.sleep(0.001)


main()
