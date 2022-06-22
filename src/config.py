# シリアルポート
PORT = "/dev/ttyAMA0"

# Fluentd のアドレス
FLUENT_HOST = "columbia.green-rabbit.net"

# sniffer.py が収集するデータの dev_id を名前に変換するテーブル
DEV_MAP = {
    # 4219: "書斎エアコン",
    0xDC17: "リビングエアコン",
}
