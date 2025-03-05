import xml.etree.ElementTree as ET
import json
from collections import defaultdict
def parse_process_data(process_data):
    # print(type(process_data))
    # str转json
    process_data_json = json.loads(process_data)
    # 提取流程的基本信息
    workflow_info = {
        "process_id": process_data_json.get("process_id", "N/A"),
        "process_name": process_data_json.get("name", "N/A"),
        "process_type": process_data_json.get("processType", "N/A")
    }
    
    print(f"流程名称: {workflow_info['process_name']}")
    print(f"流程ID: {workflow_info['process_id']}")
    print(f"流程类型: {workflow_info['process_type']}")
    print("\n审批流程节点:")

    # 提取所有节点的基本信息
    nodes = process_data_json.get("childShapes", [])
    flow = defaultdict(dict)
    node_relationships = defaultdict(list)  # 存储节点的先后关系

    for node in nodes:
        node_id = node.get("resourceId", "N/A")
        node_name = node["properties"].get("name", "未命名")
        node_type = node["stencil"]["id"]

        # 提取参与人信息和参与条件
        participant = None
        condition = None
        if "participant" in node["properties"]:
            participants = node["properties"]["participant"].get("participant", [])
            if isinstance(participants, list):
                for p in participants:
                    participant = p.get("value")
                    if "conditionExpression" in p:
                        condition = p["conditionExpression"]

        flow[node_id] = {
            "name": node_name,
            "type": node_type,
            "participant": participant,
            "condition": condition
        }

        # 输出节点信息
        print(f"- 节点: {node_name} (类型: {node_type})")
        if participant:
            print(f"  参与人: {participant}")
        if condition:
            print(f"  参与条件: {condition}")

        # 记录节点的先后关系
        for outgoing in node.get("outgoing", []):
            target = outgoing.get("resourceId")
            if target:
                node_relationships[node_id].append(target)
    
    # 输出节点的先后关系
    print("\n节点的先后关系:")
    for node_id, targets in node_relationships.items():
        node_name = flow[node_id]["name"]
        target_names = [flow[target]["name"] for target in targets]
        print(f"{node_name} -> {', '.join(target_names)}")
def parse_workflow(xml_file):
    # 解析XML文件
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # 提取流程基本信息
    wf_model = root.find(".//wf_model")
    if wf_model is None:
        print("找不到 wf_model 元素")
        return
    
    workflow = {
        "id": wf_model.find("id").text if wf_model.find("id") is not None else "N/A",
        "name": wf_model.find("name").text if wf_model.find("name") is not None else "N/A",
        "key": wf_model.find("key").text if wf_model.find("key") is not None else "N/A",
    }
    
    print(f"流程名称: {workflow['name']}")
    print(f"流程ID: {workflow['id']}")
    print(f"流程Key: {workflow['key']}")
    print("\n审批流程节点:")

    # 提取资源中的流程图数据
    resource = root.find(".//wf_resource")
    if resource is None:
        print("找不到 wf_resource 元素")
        return
    
    data = resource.find(".//data")
    if data is None:
        print("找不到 data 元素")
        return

    process_data = data.text # eval(data.text.replace("'", '"'))  # 将单引号替换为双引号以解析字典
    parse_process_data(process_data)

# 使用示例（假设XML文件名为 'workflow.xml'）
if __name__ == "__main__":
    xml_file = r"C:\Users\xyy\Downloads\Proc_ap_payapply_audit_2 (1)\Proc_ap_payapply_audit_2.xml"  # 请将此替换为实际文件路径
    workflow = parse_workflow(xml_file)
