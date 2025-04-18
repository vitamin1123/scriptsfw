import xml.etree.ElementTree as ET
import json
from collections import deque

def parse_process_file(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # 提取流程基本信息
    wf_model = root.find(".//wf_model")
    if wf_model is None:
        raise ValueError("找不到 wf_model 元素")
    
    workflow = {
        "id": wf_model.find("id").text if wf_model.find("id") is not None else "N/A",
        "name": wf_model.find("name").text if wf_model.find("name") is not None else "N/A",
        "key": wf_model.find("key").text if wf_model.find("key") is not None else "N/A",
    }
    
    print(f"流程名称: {workflow['name']}")
    print(f"流程ID: {workflow['id']}")
    print(f"流程Key: {workflow['key']}")
    print("\n审批流程节点:")
    
    # 提取流程图数据
    resource = root.find(".//wf_resource")
    if resource is None:
        raise ValueError("找不到 wf_resource 元素")
    
    data = resource.find(".//data")
    if data is None or not data.text:
        raise ValueError("找不到 data 元素")
    
    process_data = json.loads(data.text)
    return workflow, process_data

def parse_process_data(process_data):
    nodes = process_data.get("childShapes", [])
    flow = {}
    node_relationships = {}
    in_degree = {}
    
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
                condition_exp = p.get("conditionExpression", "无条件")
                participant_details.append(f"{participant_info} (条件: {condition_exp})")
        
        flow[node_id] = {
            "id": node_id,
            "name": node_name,
            "type": node_type,
            "participant": participant_details,
            "condition": condition
        }
        node_relationships[node_id] = []
        in_degree[node_id] = 0
        
    # 记录连接关系并计算入度
    for node in nodes:
        node_id = node.get("resourceId")
        for outgoing in node.get("outgoing", []):
            target = outgoing.get("resourceId")
            if target and target in flow:
                node_relationships[node_id].append(target)
                in_degree[target] += 1
    
    return flow, node_relationships, in_degree

def get_ordered_nodes(flow, node_relationships, in_degree):
    queue = deque([node for node in flow if in_degree[node] == 0])
    ordered_nodes = []
    
    while queue:
        node = queue.popleft()
        ordered_nodes.append(flow[node])
        for neighbor in node_relationships[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(ordered_nodes) != len(flow):
        print("警告: 可能存在循环依赖，部分节点未被解析！")
    
    return ordered_nodes

def main(xml_file):
    workflow, process_data = parse_process_file(xml_file)
    flow, node_relationships, in_degree = parse_process_data(process_data)
    ordered_nodes = get_ordered_nodes(flow, node_relationships, in_degree)
    
    print("\n按顺序解析的节点:")
    for node in ordered_nodes:
        print(f"- {node['name']} (类型: {node['type']}, 编码: {node['id']})")
        if node["participant"]:
            print(f"  参与人: {', '.join(node['participant'])}")
        print(f"  条件: {node['condition']}")
        
        if node["type"] == "SequenceFlow":
            sources = [src for src, targets in node_relationships.items() if node["id"] in targets]
            targets = node_relationships[node["id"]]
            source_names = [flow[src]["name"] for src in sources]
            target_names = [flow[tgt]["name"] for tgt in targets]
            print(f"  连接: {', '.join(source_names)} -> {', '.join(target_names)}")
    
if __name__ == "__main__":
    # xml_file = r"C:\Users\xyy\Downloads\Proc_er_dailyreimbursebill_audit_8 (1)\Proc_er_dailyreimbursebill_audit_8.process"
    xml_file = input("文件路径:") 
    main(xml_file)
