# シリアルポート
PORT = "/dev/ttyAMA0"

# Fluentd のアドレス
FLUENT_HOST = "columbia.green-rabbit.net"

# 中継器に記録される「INFO; Receive the report form addr = 0xXXXX」
# の「0xXXXX」を名前に変換するテーブル
DEV_MAP = {
    # 4219: "書斎エアコン",
    0xDC17: "リビングエアコン",
}
