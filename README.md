# pico-keyboard

Raspberry Pi Pico を「シリアル経由で操作できる USB キーボード」にする。
シリアルで送ったテキスト / キー操作を、Pico が USB キーボードとしてそのまま入力する。
ソフトウェアによるキー入力 (SendInput 等) を受け付けないアプリケーションで、キー入力を自動化するために使う。
OS からは物理キーボードの入力として扱われる。

```
PC (プログラム) --USBシリアル--> Pico --USB HID キーボード--> 同じ PC
```

Pico を USB ケーブル 1 本で PC に接続するだけで、キーボードとシリアルポートの複合デバイスとして認識される。

## セットアップ

### 必要なもの

- Raspberry Pi Pico (Pico / Pico W / Pico 2 / Pico 2 W のいずれか)
- **データ通信対応**の USB ケーブル (充電専用ケーブルでは認識されない)
- Python 3.8 以降 (ホスト側)

### 1. CircuitPython のダウンロード

使っているボードのページから、最新安定版の `.uf2` ファイルをダウンロードする。

| ボード | ダウンロードページ |
| --- | --- |
| Pico | https://circuitpython.org/board/raspberry_pi_pico/ |
| Pico W | https://circuitpython.org/board/raspberry_pi_pico_w/ |
| Pico 2 | https://circuitpython.org/board/raspberry_pi_pico2/ |
| Pico 2 W | https://circuitpython.org/board/raspberry_pi_pico2_w/ |

ボードが違う `.uf2` を書き込むと動かないので注意 (基板の刻印で確認できる)。

### 2. CircuitPython の書き込み

1. Pico の **BOOTSEL ボタンを押したまま** USB ケーブルで PC に接続し、接続後にボタンを離す
2. `RPI-RP2` (Pico 2 の場合は `RP2350`) という名前のドライブが現れる
3. ダウンロードした `.uf2` をそのドライブにコピーする
4. コピーが終わると Pico が自動で再起動し、`RPI-RP2` が消えて `CIRCUITPY` ドライブが現れる

### 3. ファームウェアのコピー

`firmware/` 内の次の 3 ファイルを `CIRCUITPY` ドライブの直下にコピーする
(既存の `code.py` は上書きしてよい)。

```
CIRCUITPY/
├── boot.py     ← USB デバイス構成 (キーボード + シリアル)
├── code.py     ← メイン処理
└── keymap.py   ← キー配列表
```

`lib/` フォルダや `settings.toml` など元からあるものはそのままでよい。追加ライブラリ (adafruit_hid など) は不要。

### 4. Pico を抜き差しする

`boot.py` の変更は **USB の抜き差し (またはリセット) をしないと反映されない**。
コピー後に必ず一度抜き差しする。

正しく反映されると、デバイスマネージャーの「ポート (COM と LPT)」に
**USB シリアルデバイスが 2 つ** (例: `COM5` と `COM6`) 現れる。

- 1 つ目: CircuitPython の REPL (エラーメッセージ確認用)
- 2 つ目: キー入力コマンド用 (ホストのスクリプトが使う)

ドライバーのインストールは不要 (Windows 10 以降は標準ドライバーで動作する)。

### 5. ホスト側の準備

[uv](https://docs.astral.sh/uv/) を使う。このリポジトリ内で次を実行すると、依存関係 (pyserial) がインストールされ、
`pico-keyboard` コマンドが使えるようになる。

```sh
uv sync
```

### 6. 動作確認

```sh
# 疎通確認 (何も表示されずに終われば成功)
uv run pico-keyboard -w 0

# メモ帳での入力テスト
uv run pico-keyboard -k win+r -w 1000 -t notepad -k enter -w 2000 -t "Hello, pico-keyboard!"
```

**キー入力は、その時点でフォーカスがあるウィンドウに送られる。**
ターミナルから単純に `-t` を実行すると、ターミナル自身に入力されるので注意。
手動で別ウィンドウを選ぶ場合は、先頭に `-w 3000` を付けて 3 秒以内に切り替える。

### うまく動かないとき

| 症状 | 確認すること |
| --- | --- |
| `RPI-RP2` ドライブが出ない | BOOTSEL を押したまま接続したか / ケーブルがデータ通信対応か |
| `pico-keyboard not found` | Pico を抜き差ししたか (COM ポートが 1 つしかない場合は `boot.py` が未反映) / 他のソフト (シリアルターミナル等) がポートを開いていないか |
| ポートは見つかるが応答がない | `code.py` がエラーで止まっている可能性。1 つ目の COM ポートにシリアルターミナル (Tera Term 等、115200bps) で接続するとエラー内容が見える |
| 記号がずれる | `-l us` / `-l jp` を PC のキーボード設定に合わせる |
| 文字を取りこぼす | `-d 20` など遅くする |

## 使い方

### CLI

```sh
# テキスト入力 (オプションの順序どおりに実行される)
uv run pico-keyboard -t "user" -k tab -t "p@ssw0rd" -k enter

# キー操作
uv run pico-keyboard -k ctrl+alt+delete
uv run pico-keyboard -k win+r -w 500 -t notepad -k enter

# ファイル / 標準入力の内容を入力 (改行は Enter)
uv run pico-keyboard -f script.txt
echo hello | uv run pico-keyboard -f -

# オプション
#   -p COM5    ポート指定 (省略時は自動検出)
#   -l us|jp   PC のキーボードレイアウト (既定 us)
#   -d 20      キー押下時間/間隔 ms (既定 10。取りこぼす場合は増やす)
#   --list     シリアルポート一覧
```

### Python ライブラリ

```python
from pico_keyboard import PicoKeyboard

with PicoKeyboard() as kb:          # JIS 配列の PC では layout="jp"
    kb.type("user@example.com")
    kb.key("tab")
    kb.type("password\n")        # \n は Enter
    kb.wait(1000)
    kb.key("ctrl+a", "ctrl+c")
```

エラー時 (入力できない文字、不明なキー名など) は `PicoKeyboardError` が送出される。
1 コマンド内の文字は事前に検証されるため、途中まで入力されて止まることはない。

### 別プロジェクトから使う

ホスト側ライブラリ (`host/pico_keyboard.py`) は Python パッケージ `pico-keyboard` として追加できる。
`firmware/` はパッケージに含まれない。

```sh
# GitHub から
uv add git+https://github.com/nobmurakita/pico-keyboard

# タグやブランチを固定する場合
uv add git+https://github.com/nobmurakita/pico-keyboard --tag v0.1.0

# ローカルのクローンから (編集がそのまま反映される)
uv add --editable ../pico-keyboard
```

追加後は `from pico_keyboard import PicoKeyboard` で使え、`uv run pico-keyboard` で CLI も実行できる。

## シリアルプロトコル

他の言語から直接使う場合用。1 行 1 コマンド (UTF-8 / LF 区切り)。
各コマンドの完了後に `OK` または `ERR <理由>` が 1 行返る。**応答を待ってから次を送ること。**

| コマンド | 内容 |
| --- | --- |
| `T <text>` | テキスト入力 (行末まで。1 行あたり最大 4096 バイト) |
| `K <combo> [<combo>...]` | キー/組み合わせを順に押す |
| `W <ms>` | 待機 |
| `L us` / `L jp` | PC のレイアウト設定 |
| `D <ms>` | キー押下時間/間隔 |
| `R` | 全キーを離す |
| `P` | 疎通確認 (`OK pico-keyboard`) |

### キー名

- 修飾キー: `ctrl` `shift` `alt` `win`(`gui`/`cmd`) と右側用 `rctrl` `rshift` `ralt` `rwin`
- 特殊キー: `enter` `esc` `tab` `space` `backspace` `delete` `insert` `home` `end`
  `pageup` `pagedown` `up` `down` `left` `right` `f1`〜`f24` `printscreen` `pause`
  `capslock` `numlock` `scrolllock` `menu`
- JIS 用: `zenkaku` `henkan` `muhenkan` `kana` `eisu`
- 1 文字キー: `a` `1` `/` など (`ctrl++` で Ctrl + `+`)
- 生キーコード: `0x2c` など (HID Usage ID)

組み合わせは `+` で連結: `ctrl+alt+delete` `shift+tab` `win+r`

## 注意

- 入力できるのは ASCII 印字可能文字と Tab / 改行のみ。日本語などは直接入力できない
  (IME 経由でローマ字入力させる等の工夫が必要)。
- PC の **IME がオン** だと日本語変換されてしまう。**CapsLock がオン** だと大文字/小文字が逆転する。
- レイアウト (`us`/`jp`) は PC の OS のキーボード設定に合わせる。合っていないと記号がずれる。
- 入力を取りこぼす場合は `-d` を大きくする。
- PC には `CIRCUITPY` ドライブも見える。見せたくない場合は `boot.py` のコメントを参照。
