from common.comms.node_client import AlarmNode

if __name__ == "__main__":
    node = AlarmNode()
    node.start_discovery()