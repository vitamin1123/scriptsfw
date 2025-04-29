import xml.etree.ElementTree as ET
import pandas as pd
from collections import defaultdict

def parse_bpmn_xml(xml_file):
    # 解析XML文件
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # 提取流程基本信息
    process_info = {}
    wf_model = root.find(".//wf_model")
    if wf_model is not None:
        process_info['id'] = wf_model.find('id').text if wf_model.find('id') is not None else ''
        process_info['key'] = wf_model.find('key').text if wf_model.find('key') is not None else ''
        process_info['name'] = wf_model.find('name').text if wf_model.find('name') is not None else ''
        process_info['description'] = wf_model.find('description').text if wf_model.find('description') is not None else ''
        process_info['version'] = wf_model.find('version').text if wf_model.find('version') is not None else ''
    
    # 提取流程图形数据
    wf_resource = root.find(".//wf_resource")
    graph_data = None
    if wf_resource is not None:
        multilanguagetext = wf_resource.find(".//multilanguagetext/locale/content")
        if multilanguagetext is not None and multilanguagetext.text:
            import json
            try:
                graph_data = json.loads(multilanguagetext.text)
            except json.JSONDecodeError:
                pass
    
    # 提取节点和边信息
    nodes = {}
    edges = {}
    
    if graph_data and 'data' in graph_data and 'childShapes' in graph_data['data']:
        for shape in graph_data['data']['childShapes']:
            if 'properties' in shape and 'itemId' in shape['properties']:
                item_id = shape['properties']['itemId']
                
                # 处理节点
                if shape['stencil']['id'] in ['StartSignalEvent', 'UserTask', 'AuditTask', 'YunzhijiaTask', 'EndNoneEvent']:
                    node_info = {
                        'id': item_id,
                        'type': shape['stencil']['id'],
                        'name': shape['properties'].get('name', ''),
                        'participants': [],
                        'conditions': [],
                        'decision_options': []
                    }
                    
                    # 提取参与者信息
                    if 'participant' in shape['properties']:
                        participants = shape['properties']['participant']
                        if isinstance(participants, dict) and 'participant' in participants:
                            for participant in participants['participant']:
                                if isinstance(participant, dict):
                                    part_info = {
                                        'type': participant.get('type', ''),
                                        'value': participant.get('value', ''),
                                        'condition': participant.get('conditionExpression', '')
                                    }
                                    node_info['participants'].append(part_info)
                    
                    # 提取决策选项
                    if 'decisionOptions' in shape['properties']:
                        for option in shape['properties']['decisionOptions']:
                            if isinstance(option, dict):
                                opt_info = {
                                    'name': option.get('name', ''),
                                    'type': option.get('auditType', ''),
                                    'reject_to': []
                                }
                                if 'rejectOptions' in option:
                                    for reject_opt in option['rejectOptions']:
                                        if isinstance(reject_opt, dict):
                                            opt_info['reject_to'].append(reject_opt.get('name', ''))
                                node_info['decision_options'].append(opt_info)
                    
                    nodes[item_id] = node_info
                
                # 处理边
                elif shape['stencil']['id'] == 'SequenceFlow':
                    edge_info = {
                        'id': item_id,
                        'source': shape.get('source', {}).get('resourceId', ''),
                        'target': shape.get('target', {}).get('resourceId', ''),
                        'condition': shape['properties'].get('conditionExpression', '')
                    }
                    edges[item_id] = edge_info
    
    # 构建流程图
    graph = defaultdict(list)
    for edge in edges.values():
        graph[edge['source']].append((edge['target'], edge['id']))
    
    # 查找所有路径
    def find_all_paths(start, end, path=None, paths=None):
        if path is None:
            path = []
        if paths is None:
            paths = []
        
        path = path + [start]
        
        if start == end:
            paths.append(path)
            return
        
        for node, _ in graph.get(start, []):
            if node not in path:
                find_all_paths(node, end, path, paths)
        
        return paths
    
    # 查找开始和结束节点
    start_nodes = [node_id for node_id, node in nodes.items() if node['type'] == 'StartSignalEvent']
    end_nodes = [node_id for node_id, node in nodes.items() if node['type'] == 'EndNoneEvent']
    
    all_paths = []
    for start in start_nodes:
        for end in end_nodes:
            paths = find_all_paths(start, end)
            all_paths.extend(paths)
    
    # 准备输出数据
    output_data = []
    
    # 添加流程信息
    output_data.append({
        "类型": "流程信息",
        "ID": process_info.get('id', ''),
        "名称": process_info.get('name', ''),
        "Key": process_info.get('key', ''),
        "版本": process_info.get('version', ''),
        "描述": process_info.get('description', ''),
        "参与者": "",
        "条件": ""
    })
    
    # 添加路径信息
    for i, path in enumerate(all_paths, 1):
        path_name = f"路径 {i}"
        first_node = True
        
        for node_id in path:
            node = nodes.get(node_id, {})
            
            # 获取参与者信息
            participants = []
            for part in node.get('participants', []):
                part_str = f"{part['type']}: {part['value']}"
                if part['condition']:
                    part_str += f" (条件: {part['condition']})"
                participants.append(part_str)
            
            # 获取决策选项
            decisions = []
            for opt in node.get('decision_options', []):
                opt_str = f"{opt['name']} ({opt['type']})"
                if opt['reject_to']:
                    opt_str += f" → {'/'.join(opt['reject_to'])}"
                decisions.append(opt_str)
            
            output_data.append({
                "类型": "节点",
                "路径": path_name,
                "ID": node_id,
                "名称": node.get('name', ''),
                "节点类型": node.get('type', ''),
                "参与者": "\n".join(participants),
                "决策选项": "\n".join(decisions),
                "条件": ""
            })
            
            # 如果不是最后一个节点，添加边信息
            if node_id != path[-1]:
                next_node_id = path[path.index(node_id)+1]
                edge_id = None
                for e in edges.values():
                    if e['source'] == node_id and e['target'] == next_node_id:
                        edge_id = e['id']
                        break
                
                if edge_id:
                    edge = edges.get(edge_id, {})
                    output_data.append({
                        "类型": "连接线",
                        "路径": path_name,
                        "ID": edge_id,
                        "名称": f"{node.get('name', '')} → {nodes.get(next_node_id, {}).get('name', '')}",
                        "节点类型": "SequenceFlow",
                        "参与者": "",
                        "决策选项": "",
                        "条件": edge.get('condition', '')
                    })
    
    # 转换为DataFrame
    df = pd.DataFrame(output_data)
    
    return process_info, nodes, edges, all_paths, df

# 使用示例
if __name__ == "__main__":
    xml_file = input("文件路径:") 
    process_info, nodes, edges, all_paths, df = parse_bpmn_xml(xml_file)
    
    # 打印流程信息
    print(f"流程名称: {process_info.get('name', '')}")
    print(f"流程ID: {process_info.get('id', '')}")
    print(f"版本: {process_info.get('version', '')}")
    print("\n流程路径:")
    
    # 打印所有路径
    for i, path in enumerate(all_paths, 1):
        path_names = [nodes.get(node_id, {}).get('name', node_id) for node_id in path]
        print(f"路径 {i}: {' → '.join(path_names)}")
    
    # 保存到Excel
    # output_file = "bpmn_analysis.xlsx"
    # df.to_excel(output_file, index=False)
    # print(f"\n分析结果已保存到: {output_file}")