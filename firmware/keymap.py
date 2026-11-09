# 文字 / キー名 → HID キーコード 変換テーブル
# ホスト側 OS のキーボードレイアウト設定 (US / JIS) に合わせて選択する。

# 修飾キー (HID レポート先頭バイトのビット)
MODIFIERS = {
    "ctrl": 0x01, "lctrl": 0x01, "control": 0x01,
    "shift": 0x02, "lshift": 0x02,
    "alt": 0x04, "lalt": 0x04, "option": 0x04,
    "gui": 0x08, "lgui": 0x08, "win": 0x08, "cmd": 0x08, "meta": 0x08, "super": 0x08,
    "rctrl": 0x10,
    "rshift": 0x20,
    "ralt": 0x40, "altgr": 0x40,
    "rgui": 0x80, "rwin": 0x80,
}
SHIFT = 0x02

# 名前付きキー (レイアウト非依存)
NAMED_KEYS = {
    "enter": 0x28, "return": 0x28,
    "esc": 0x29, "escape": 0x29,
    "backspace": 0x2A, "bs": 0x2A,
    "tab": 0x2B,
    "space": 0x2C,
    "capslock": 0x39,
    "printscreen": 0x46, "prtsc": 0x46,
    "scrolllock": 0x47,
    "pause": 0x48, "break": 0x48,
    "insert": 0x49, "ins": 0x49,
    "home": 0x4A,
    "pageup": 0x4B, "pgup": 0x4B,
    "delete": 0x4C, "del": 0x4C,
    "end": 0x4D,
    "pagedown": 0x4E, "pgdn": 0x4E,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
    "numlock": 0x53,
    "menu": 0x65, "app": 0x65, "application": 0x65,
    # JIS 固有キー
    "zenkaku": 0x35, "hankaku": 0x35,
    "kana": 0x88, "katakanahiragana": 0x88,
    "henkan": 0x8A,
    "muhenkan": 0x8B,
    "eisu": 0x91, "lang2": 0x91, "lang1": 0x90,
}
for _i in range(12):
    NAMED_KEYS["f%d" % (_i + 1)] = 0x3A + _i   # F1-F12
for _i in range(12):
    NAMED_KEYS["f%d" % (_i + 13)] = 0x68 + _i  # F13-F24


def _common():
    # 英数字・スペース・制御文字 (US / JIS 共通)
    m = {}
    for i in range(26):
        m[chr(ord("a") + i)] = (0x04 + i, 0)
        m[chr(ord("A") + i)] = (0x04 + i, SHIFT)
    for i in range(9):
        m[chr(ord("1") + i)] = (0x1E + i, 0)
    m["0"] = (0x27, 0)
    m[" "] = (0x2C, 0)
    m["\t"] = (0x2B, 0)
    m["\n"] = (0x28, 0)
    return m


def _build(pairs):
    m = _common()
    for code, normal, shifted in pairs:
        if normal:
            m[normal] = (code, 0)
        if shifted:
            m[shifted] = (code, SHIFT)
    return m


# (キーコード, 通常, Shift時)
US = _build((
    (0x1E, None, "!"), (0x1F, None, "@"), (0x20, None, "#"), (0x21, None, "$"),
    (0x22, None, "%"), (0x23, None, "^"), (0x24, None, "&"), (0x25, None, "*"),
    (0x26, None, "("), (0x27, None, ")"),
    (0x2D, "-", "_"), (0x2E, "=", "+"), (0x2F, "[", "{"), (0x30, "]", "}"),
    (0x31, "\\", "|"), (0x33, ";", ":"), (0x34, "'", '"'), (0x35, "`", "~"),
    (0x36, ",", "<"), (0x37, ".", ">"), (0x38, "/", "?"),
))

JP = _build((
    (0x1E, None, "!"), (0x1F, None, '"'), (0x20, None, "#"), (0x21, None, "$"),
    (0x22, None, "%"), (0x23, None, "&"), (0x24, None, "'"), (0x25, None, "("),
    (0x26, None, ")"),
    (0x2D, "-", "="), (0x2E, "^", "~"), (0x2F, "@", "`"), (0x30, "[", "{"),
    (0x32, "]", "}"), (0x33, ";", "+"), (0x34, ":", "*"),
    (0x36, ",", "<"), (0x37, ".", ">"), (0x38, "/", "?"),
    (0x87, "\\", "_"),   # ろ キー
    (0x89, None, "|"),   # ¥ キー
))

LAYOUTS = {"us": US, "jp": JP, "jis": JP}


def parse_combo(combo, layout):
    """'ctrl+alt+delete' / 'shift+tab' / 'ctrl+c' / 'a' → (modifier, keycode)"""
    mod = 0
    key = 0
    # '+' 単体や 'ctrl++' のようにキー自体が '+' の場合に対応
    if combo == "+" or combo.endswith("++"):
        parts = combo[:-2].split("+") if len(combo) > 1 else []
        parts.append("+")
    else:
        parts = combo.split("+")
    for p in parts:
        if p == "":
            raise ValueError("bad combo: " + combo)
        name = p.lower() if len(p) > 1 else p
        if name in MODIFIERS:
            mod |= MODIFIERS[name]
            continue
        if key:
            raise ValueError("multiple keys in combo: " + combo)
        if name in NAMED_KEYS:
            key = NAMED_KEYS[name]
        elif len(name) == 1:
            ch = name
            # 'ctrl+C' のような大文字指定は 'ctrl+c' と同じに扱う
            if "A" <= ch <= "Z":
                ch = ch.lower()
            if ch not in layout:
                raise ValueError("unknown key: " + p)
            code, m = layout[ch]
            key = code
            mod |= m
        elif name.startswith("0x"):
            key = int(name, 16)  # 生キーコード指定
        else:
            raise ValueError("unknown key: " + p)
    return mod, key
