# USB デバイス構成 (変更後は Pico の再接続 / リセットが必要)
import usb_cdc
import usb_hid

# console: REPL 用シリアル, data: コマンド受付用シリアル
usb_cdc.enable(console=True, data=True)

# HID はキーボードのみ (マウス等は無効)
usb_hid.enable((usb_hid.Device.KEYBOARD,))

# PC に CIRCUITPY ドライブを見せたくない場合は以下を有効化する。
# (無効化後にファイルを編集したいときは、GP15 を GND に繋いで起動するなどの
#  解除手段を自分で用意すること)
# import storage
# storage.disable_usb_drive()
