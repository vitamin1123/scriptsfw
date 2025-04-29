import xml.etree.ElementTree as ET
import json
from collections import defaultdict
from bpmn_python import bpmn_diagram_rep as diagram
from bpmn_python import bpmn_diagram_visualizer as visualizer
import oracledb
from oracle_db_wrapper import OracleDBWrapper

class DataResolver:
    def __init__(self):
        self.user = "JD_CW"
        self.password = "JD_CW"
        self.instant_client_dir = r"C:\Users\xyy\Desktop\instantclient_11_2"
        self.host = '10.0.1.91'
        self.port = '1521'
        self.service_name = 'orcl'
        self.dsn = oracledb.makedsn(self.host, self.port, service_name=self.service_name)
        self.db = OracleDBWrapper(self.user, self.password, self.dsn, self.instant_client_dir)
        self.db.connect()
        
    def get_user_name(self, user_id):
        if not user_id or user_id == "N/A":
            return "N/A"
        query = f"select ftruename from cosmic_sys.t_sec_user where fid = '{user_id}'"
        results = self.db.execute_query(query)
        return results[0][0] if results else user_id
        
    def get_expense_item(self, item_id):
        if not item_id or item_id == "N/A":
            return "N/A"
        query = f"select fnumber, ffullname from cosmic_sys.t_er_expenseitem where fid = '{item_id}'"
        results = self.db.execute_query(query)
        return f"{results[0][0]}-{results[0][1]}" if results else item_id
        
    def get_role_info(self, role_id):
        if not role_id or role_id == "N/A":
            return "N/A"
        query = f"""
        select b.ftruename, c.fname 
        from cosmic_sys.t_wf_roleentry a 
        left join cosmic_sys.t_sec_user b on a.fuser = b.fid 
        left join cosmic_sys.t_org_org c on a.forg = c.fid 
        where a.fid = '{role_id}'
        """
        results = self.db.execute_query(query)
        if not results:
            return "N/A"
        return "，".join([f"[{row[0] if row[0] else 'N/A'}, {row[1] if row[1] else 'N/A'}]" for row in results])
        
    def get_org_name(self, org_id):
        if not org_id or org_id == "N/A":
            return "N/A"
        query = f"select fname from cosmic_sys.t_org_org where fid = '{org_id}'"
        results = self.db.execute_query(query)
        return results[0][0] if results else org_id
        
    def close(self):
        self.db.close()

def parse_participant(participant, resolver):
    if not participant:
        return []
    
    parsed = []
    for p in participant:
        if isinstance(p, dict):
            role_id = p.get('roleId', 'N/A')
            participant_value = p.get('value', 'N/A')
            
            if participant_value.isdigit():
                participant_name = resolver.get_user_name(participant_value)
            else:
                participant_name = participant_value
            
            role_info = resolver.get_role_info(role_id) if role_id != 'N/A' else 'N/A'
            parsed.append(f"{participant_name} (角色编号: {role_info})")
        else:
            parsed.append(resolver.get_user_name(p))
    
    return parsed

def parse_process_file(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Parse workflow basic info
    wf_model = root.find(".//wf_model")
    if wf_model is None:
        raise ValueError("找不到 wf_model 元素")
    
    workflow = {
        "id": wf_model.find("id").text if wf_model.find("id") is not None else "N/A",
        "name": wf_model.find("name").text if wf_model.find("name") is not None else "N/A",
        "key": wf_model.find("key").text if wf_model.find("key") is not None else "N/A",
        "description": wf_model.find("description").text if wf_model.find("description") is not None else "",
        "version": wf_model.find("version").text if wf_model.find("version") is not None else ""
    }
    
    # Parse resource data
    resource = root.find(".//wf_resource")
    if resource is None:
        raise ValueError("找不到 wf_resource 元素")
    
    data = resource.find(".//data")
    if data is None or not data.text:
        raise ValueError("找不到 data 元素")
    
    try:
        process_data = json.loads(data.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"解析JSON数据失败: {e}")
    
    return workflow, process_data

def build_dag_with_bpmn_python(process_data, resolver):
    bpmn_graph = diagram.BpmnDiagramGraph()
    bpmn_graph.create_new_diagram(diagram_name="Process")
    
    # Create nodes
    node_mapping = {}
    node_info = {}
    
    for node in process_data.get("childShapes", []):
        node_id = node.get("resourceId", "N/A")
        properties = node.get("properties", {})
        
        stencil_id = node["stencil"]["id"]
        node_name = properties.get("name", "未命名")
        
        # Map stencil types to BPMN types
        bpmn_type = {
            "StartSignalEvent": "startEvent",
            "EndNoneEvent": "endEvent",
            "UserTask": "userTask",
            "AuditTask": "userTask",
            "YunzhijiaTask": "userTask",
            "SequenceFlow": "sequenceFlow"
        }.get(stencil_id, "task")
        
        if bpmn_type == "startEvent":
            bpmn_graph.add_start_event_to_diagram(node_id, node_name=node_name)
        elif bpmn_type == "endEvent":
            bpmn_graph.add_end_event_to_diagram(node_id, node_name=node_name)
        elif bpmn_type == "sequenceFlow":
            # Will handle in next step
            continue
        else:
            bpmn_graph.add_task_to_diagram(node_id, node_name=node_name)
        
        node_mapping[node_id] = node_id
        node_info[node_id] = {
            "name": node_name,
            "type": stencil_id,
            "participant": parse_participant(properties.get("participant", {}).get("participant", []), resolver),
            "properties": {k: v for k, v in properties.items() if k not in ["participant", "conditionalRule"]}
        }
    
    # Create edges
    for node in process_data.get("childShapes", []):
        node_id = node.get("resourceId")
        for outgoing in node.get("outgoing", []):
            target = outgoing.get("resourceId")
            if target in node_mapping:
                flow_id = f"flow_{node_id}_{target}"
                bpmn_graph.add_sequence_flow_to_diagram(node_id, target, flow_id)
    
    # Build DAG structure similar to original code
    graph = defaultdict(list)
    for flow in bpmn_graph.flows.values():
        graph[flow.from_task].append(flow.to_task)
    
    return graph, node_info

def dfs(graph, node_info, path, current_node, all_paths):
    path.append(current_node)
    
    if not graph.get(current_node, []):  # End node
        all_paths.append(list(path))
    else:
        for neighbor in graph.get(current_node, []):
            dfs(graph, node_info, path, neighbor, all_paths)
    
    path.pop()

def find_all_paths(graph, node_info):
    # Find start nodes (nodes with no incoming edges)
    all_targets = set()
    for targets in graph.values():
        all_targets.update(targets)
    
    start_nodes = [node for node in node_info if node not in all_targets]
    all_paths = []
    
    for start in start_nodes:
        dfs(graph, node_info, [], start, all_paths)
    
    return all_paths

def main(xml_file):
    resolver = DataResolver()
    
    try:
        workflow, process_data = parse_process_file(xml_file)
        graph, node_info = build_dag_with_bpmn_python(process_data, resolver)
        all_paths = find_all_paths(graph, node_info)
        
        print(f"流程名称: {workflow['name']}")
        print(f"流程ID: {workflow['id']}")
        print(f"流程Key: {workflow['key']}")
        print("\n所有可能的路径:")
        
        for idx, path in enumerate(all_paths, 1):
            print(f"路径 {idx}:")
            for node in path:
                info = node_info[node]
                print(f"  - {info['name']} (类型: {info['type']})")
                if info["participant"]:
                    print(f"    参与人: {', '.join(info['participant'])}")
            print()
    finally:
        resolver.close()

if __name__ == "__main__":
    xml_file = input("文件路径:")
    main(xml_file)