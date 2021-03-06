import sys

import requests
import requests as req
import json

import deleteIntents
import dijkstra
import input_data
import matrix


def get_ip():
    with open("D:/Scripts/vmIP.txt", "r") as f:
        ip = f.readline().strip()
    return ip


USER = ("onos", "rocks")


def get_links():
    try:
        res = req.get(f"http://{IP}:8181/onos/v1/links", auth=USER)
        links = res.json()["links"]
        with open("topology_links.json", "w") as f:
            f.write(json.dumps(res.json(), indent=4))
        print(json.dumps(res.json(), indent=4))
        return links
    except requests.exceptions.ConnectionError:
        print("Oops. Seems like dns lookup failed..")
        sys.exit()


class Path:
    def __init__(self, *args):
        self.list = [x for x in args]


class HostPair:
    def __init__(self, h1, h2):
        self.h1 = h1
        self.h2 = h2

    def get_dst_host_num(self):
        return self.h2[1:]


def get_points(path_list):
    points = Path()
    for list in path_list:
        nodes = list[1]
        if nodes[-1].data[-1] == hex(int(host_pair.get_dst_host_num()))[2:]:
            num_nodes = [int(_.data[-1], 16) for _ in nodes]
            points.list = num_nodes
            print()
    return points


def make_intent(points, links):
    intents = []
    for point in range(0, len(points.list)):
        portIn = ""
        portOut = ""
        deviceId = f"of:000000000000000{hex(points.list[point])[2:]}"
        intent = {
            "type": "PointToPointIntent",
            "appId": "org.onosproject.cli",
            "priority": 100,
            "ingressPoint": {
                "port": f"{portIn}",
                "device": deviceId
            },
            "egressPoint": {
                "port": f"{portOut}",
                "device": deviceId
            }
        }
        for link in links:
            if link["src"]["device"] == deviceId and int(link["dst"]["device"][-1], 16) in points.list:
                if point < 1:
                    intent["ingressPoint"]["port"] = "1"
                if (link["dst"]["device"] == f"of:000000000000000{hex(points.list[point - 1])[2:]}"
                        and points.list[point - 1] in points.list):
                    portIn = link["src"]["port"]
                    intent["ingressPoint"]["port"] = portIn
                if point + 1 > len(points.list) - 1:
                    intent["egressPoint"]["port"] = "1"
                elif (link["dst"]["device"] == f"of:000000000000000{hex(points.list[point + 1])[2:]}"
                      and points.list[point + 1] in points.list):
                    portOut = link["src"]["port"]
                    intent["egressPoint"]["port"] = portOut
                else:
                    continue
        intents.append(intent)
        continue
    return intents


def post_intents(data):
    intents_num = len(data["intents"])
    successful_requests = 0
    for intent in data["intents"]:
        res = req.post(f"http://{IP}:8181/onos/v1/intents", json=intent, auth=USER)
        if res.status_code == 200:
            successful_requests += 1
    if successful_requests == intents_num:
        print(f"{successful_requests}/{intents_num} were successfully sent")
    else:
        print(f"Oops. Only {successful_requests}/{intents_num} were successfully sent")


def get_devices_list(links):
    devices = []
    for link in links:
        devices.append(link["src"]["device"])
    devices = list(set(devices))
    devices.sort()
    return devices


def get_nodes(devices):
    nodes = []
    for device in devices:
        nodes.append(dijkstra.Node(device))
    return nodes


if __name__ == '__main__':
    IP = get_ip()

    links = get_links()

    devices = get_devices_list(links)

    nodes = get_nodes(devices)
    print(nodes)

    graph = dijkstra.Graph.create_from_nodes(nodes)

    #################### No weights ######################
    # Common adjacency matrix that tells us about the switches connections
    graph.adj_mat = matrix.get_matrix(links, len(devices))
    ##################### Weights ########################
    # graph.adj_mat = input_data.main()

    graph.print_adj_mat()
    start_node = graph.get_node_by_data("of:0000000000000001")
    print([(weight, [n.data for n in node]) for (weight, node) in graph.dijkstra(start_node)])
    path_list = graph.dijkstra(start_node)

    #####################################################################

    host_pair = HostPair("h1", "h10")
    points = get_points(path_list)
    print(points.list)

    intents = {"intents": make_intent(points, links)}
    points.list.reverse()
    intents["intents"].extend(make_intent(points, links))
    data = intents
    print("\n")
    print(json.dumps(data, indent=4))

    deleteIntents.clear()
    post_intents(intents)

    while True:
        src, dst, w = map(int, input("Input src, dst, w:\n").split())
        if graph.set_new_weight(src, dst, w):
            path_list = graph.dijkstra(start_node)
            print([(weight, [n.data for n in node]) for (weight, node) in graph.dijkstra(start_node)])

            points = get_points(path_list)
            print(points.list)

            intents = {"intents": make_intent(points, links)}
            points.list.reverse()
            intents["intents"].extend(make_intent(points, links))

            deleteIntents.clear()
            post_intents(intents)
