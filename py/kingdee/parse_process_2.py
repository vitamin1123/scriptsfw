import xml.etree.ElementTree as ET
import json
from collections import defaultdict

def parse_process_file(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    wf_model = root.find(".//wf_model")
    if wf_model is None:
        raise ValueError("找不到 wf_model 元素")
    
    workflow = {
        "id": wf_model.find("id").text if wf_model.find("id") is not None else "N/A",
        "name": wf_model.find("name").text if wf_model.find("name") is not None else "N/A",
        "key": wf_model.find("key").text if wf_model.find("key") is not None else "N/A",
    }
    
    resource = root.find(".//wf_resource")
    if resource is None:
        raise ValueError("找不到 wf_resource 元素")
    
    data = resource.find(".//data")
    if data is None or not data.text:
        raise ValueError("找不到 data 元素")
    
    process_data = json.loads(data.text)
    return workflow, process_data

def build_dag(process_data):
    nodes = process_data.get("childShapes", [])
    graph = defaultdict(list)
    node_info = {}
    
    for node in nodes:
        node_id = node.get("resourceId", "N/A")
        node_name = node["properties"].get("name", "未命名")
        node_type = node["stencil"]["id"]
        participant = node["properties"].get("participant", {}).get("participant", [])
        condition = node["properties"].get("conditionalRule", "无条件")
        
        participant_details = []
        if isinstance(participant, list):
            for p in participant:
                participant_info = p.get("value", "N/A")
                role_id = p.get("roleId", "N/A")  # 获取角色编号
                condition_exp = p.get("conditionExpression", "无条件")
                participant_details.append(f"{participant_info} (角色编号: {role_id}(条件: {condition_exp})")
        
        node_info[node_id] = {
            "name": node_name,
            "type": node_type,
            "participant": participant_details,
            "condition": condition
        }
        
    for node in nodes:
        node_id = node.get("resourceId")
        for outgoing in node.get("outgoing", []):
            target = outgoing.get("resourceId")
            if target in node_info:
                graph[node_id].append(target)
    
    return graph, node_info

def dfs(graph, node_info, path, current_node, all_paths):
    path.append(current_node)
    
    if not graph[current_node]:  # 终点节点
        all_paths.append(list(path))
    else:
        for neighbor in graph[current_node]:
            dfs(graph, node_info, path, neighbor, all_paths)
    
    path.pop()

def find_all_paths(graph, node_info):
    start_nodes = [node for node in node_info if all(node not in targets for targets in graph.values())]
    all_paths = []
    
    for start in start_nodes:
        dfs(graph, node_info, [], start, all_paths)
    
    return all_paths

def main(xml_file):
    workflow, process_data = parse_process_file(xml_file)
    graph, node_info = build_dag(process_data)
    all_paths = find_all_paths(graph, node_info)
    
    print(f"流程名称: {workflow['name']}")
    print(f"流程ID: {workflow['id']}")
    print(f"流程Key: {workflow['key']}")
    print("\n所有可能的路径:")
    
    for idx, path in enumerate(all_paths, 1):
        print(f"路径 {idx}:")
        for node in path:
            info = node_info[node]
            print(f"  - {info['name']} (类型: {info['type']}), 条件: {info['condition']})")
            if info["participant"]:
                print(f"    参与人: {', '.join(info['participant'])}")
        print()
    
if __name__ == "__main__":
    # xml_file = "/Users/xyy/Downloads/Proc_er_dailyreimbursebill_audit_8.xml"
    xml_file  = input("文件路径:") 
    main(xml_file)
