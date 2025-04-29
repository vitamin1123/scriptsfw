import xml.etree.ElementTree as ET
import json
from collections import defaultdict
import oracledb
import re
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
        
        # 初始化所有ID映射字典
        self._init_all_mappings()
    
    def _init_all_mappings(self):
        """初始化所有ID到名称的映射字典"""
        # 用户ID映射
        self.user_map = self._get_user_mapping()
        # 费用项目ID映射
        self.expense_item_map = self._get_expense_item_mapping()
        # 组织ID映射
        self.org_map = self._get_org_mapping()
        # 角色ID映射
        self.role_map = self._get_role_mapping()
    
    def _get_user_mapping(self):
        """获取所有用户ID到名称的映射"""
        query = "select fid, ftruename from cosmic_sys.t_sec_user"
        results = self.db.execute_query(query)
        return {row[0]: row[1] for row in results} if results else {}
    
    def _get_expense_item_mapping(self):
        """获取所有费用项目ID到名称的映射"""
        query = "select fid, fnumber, ffullname from cosmic_sys.t_er_expenseitem"
        results = self.db.execute_query(query)
        return {row[0]: f"{row[1]}-{row[2]}" for row in results} if results else {}
    
    def _get_org_mapping(self):
        """获取所有组织ID到名称的映射"""
        query = "select fid, fname from cosmic_sys.t_org_org"
        results = self.db.execute_query(query)
        return {row[0]: row[1] for row in results} if results else {}
    
    def _get_role_mapping(self):
        """获取所有角色ID到信息的映射"""
        query = """
        select a.fid, b.ftruename, c.fname 
        from cosmic_sys.t_wf_roleentry a 
        left join cosmic_sys.t_sec_user b on a.fuser = b.fid 
        left join cosmic_sys.t_org_org c on a.forg = c.fid
        """
        results = self.db.execute_query(query)
        role_map = {}
        if results:
            for row in results:
                role_id = row[0]
                if role_id not in role_map:
                    role_map[role_id] = []
                role_map[role_id].append(f"[{row[1] if row[1] else 'N/A'}, {row[2] if row[2] else 'N/A'}]")
        return role_map
    
    def get_user_name(self, user_id):
        """从预加载的字典获取用户名"""
        return self.user_map.get(user_id, user_id)
        
    def get_expense_item(self, item_id):
        """从预加载的字典获取费用项目"""
        return self.expense_item_map.get(item_id, item_id)
        
    def get_role_info(self, role_id):
        """从预加载的字典获取角色信息"""
        return "，".join(self.role_map.get(role_id, ["N/A"]))
        
    def get_org_name(self, org_id):
        """从预加载的字典获取组织名"""
        return self.org_map.get(org_id, org_id)
        
    def get_expense_items_by_ids(self, item_ids):
        """从预加载的字典批量获取费用项目"""
        if not item_ids:
            return "N/A"
            
        try:
            # 统一处理输入为列表
            if isinstance(item_ids, str):
                # 尝试解析JSON数组
                if item_ids.startswith('[') and item_ids.endswith(']'):
                    try:
                        items = json.loads(item_ids)
                        if isinstance(items, list):
                            id_list = [str(item.get('value', '')) for item in items]
                        else:
                            return "N/A"
                    except json.JSONDecodeError:
                        # 处理逗号分隔的ID字符串
                        item_ids = item_ids.strip('[]"\'')
                        id_list = [id_.strip() for id_ in item_ids.split(',')]
                else:
                    # 直接是逗号分隔的ID字符串
                    item_ids = item_ids.strip('"\'')
                    id_list = [id_.strip() for id_ in item_ids.split(',')]
            elif isinstance(item_ids, list):
                id_list = [str(id_) for id_ in item_ids]
            else:
                return "N/A"
            
            # 过滤空值
            id_list = [id_ for id_ in id_list if id_]
            if not id_list:
                return "N/A"
            
            # 从预加载的字典获取名称
            resolved_items = []
            for id_ in id_list:
                resolved_items.append(self.expense_item_map.get(id_, f"未知项目({id_})"))
                    
            return "、".join(resolved_items)
            
        except Exception as e:
            print(f"解析费用项目出错: {e}")
            return "N/A"
        
    def close(self):
        self.db.close()
def _parse_raw_condition_string(condition_str, resolver):
    """处理原始字符串类型的条件"""
    # 先处理已知的变量引用
    var_mapping = {
        'model.expenseentryentity.expenseitem.id': ('费用项目', 'expenseitem'),
        'model.applier.id': ('申请人', 'user'),
        'model.org.id': ('组织', 'org'),
        'model.company.id': ('公司', 'org'),
        'model.billno': ('单据编号', None),
        'model.loanamount': ('借款金额', None)
    }
    
    # 替换变量名和操作符
    op_map = {
        'IN': '在',
        'NI': '不在',
        '==': '等于',
        '!=': '不等于',
        '>': '大于',
        '<': '小于',
        '>=': '大于等于',
        '<=': '小于等于',
        '&&': '且',
        '||': '或',
        '&amp;&amp;': '且'
    }
    
    # 第一步：替换已知的变量引用
    for var, (name, _) in var_mapping.items():
        condition_str = condition_str.replace(var, name)
    
    # 第二步：替换操作符
    for op, name in op_map.items():
        condition_str = condition_str.replace(op, name)
    
    # 第三步：处理所有19位数字ID（从预加载的字典中查找）
    def replace_id(match):
        id_ = match.group(1)
        # 尝试从各个映射字典中查找
        if id_ in resolver.expense_item_map:
            return resolver.expense_item_map[id_]
        elif id_ in resolver.user_map:
            return resolver.user_map[id_]
        elif id_ in resolver.org_map:
            return resolver.org_map[id_]
        return id_  # 找不到则返回原值
    
    condition_str = re.sub(r'(\d{19})', replace_id, condition_str)
    
    return condition_str
def parse_condition(condition, resolver):
    if not condition or condition == "无条件":
        return "无条件"
    
    # 预处理：尝试解析JSON字符串
    if isinstance(condition, str):
        try:
            condition = json.loads(condition)
        except json.JSONDecodeError:
            # 不是JSON字符串，直接处理原始字符串
            return _parse_raw_condition_string(condition, resolver)
    
    if isinstance(condition, dict):
        expression = condition.get('expression', '')
        entry_entities = condition.get('entryentity', [])
        
        # 替换表达式中的变量名
        var_mapping = {
            'model.expenseentryentity.expenseitem.id': '费用项目',
            'model.applier.id': '申请人',
            'model.org.id': '组织',
            'model.company.id': '公司',
            'model.billno': '单据编号',
            'model.loanamount': '借款金额'
        }
        
        for var, name in var_mapping.items():
            expression = expression.replace(var, name)
        
        # 处理每个条件条目
        for entry in entry_entities:
            param = entry.get('paramnumber', '')
            operation = entry.get('operation', '')
            value = entry.get('value', '')
            logic = entry.get('logic', '')
            
            # 获取参数显示名称
            param_name = var_mapping.get(param, param)
            
            # 解析参数值
            parsed_value = _parse_condition_value(param, value, resolver)
            
            # 替换操作符
            op_map = {
                'IN': '在',
                'NI': '不在',  # NI表示NOT IN
                '==': '等于',
                '!=': '不等于',
                '>': '大于',
                '<': '小于',
                '>=': '大于等于',
                '<=': '小于等于'
            }
            operation = op_map.get(operation, operation)
            
            # 构建条件部分
            condition_part = f"{param_name} {operation} {parsed_value}"
            
            # 处理括号
            if entry.get('leftbracket', ''):
                condition_part = f"{entry['leftbracket']}{condition_part}"
            if entry.get('rightbracket', ''):
                condition_part = f"{condition_part}{entry['rightbracket']}"
            
            # 处理逻辑运算符
            if logic:
                logic_map = {'&&': '且', '||': '或'}
                condition_part = f" {logic_map.get(logic, logic)} {condition_part}"
            
            # 替换表达式中的占位符
            placeholder = f"${{ {param} {operation} {value} }}"
            expression = expression.replace(placeholder, condition_part)
        
        return expression.replace('${', '').replace('}', '')
    
    return str(condition)



def _parse_condition_value(param, value, resolver):
    """解析条件中的值"""
    if not value or value == "N/A":
        return "N/A"
    
    try:
        # 处理JSON数组
        if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
            try:
                items = json.loads(value)
                if isinstance(items, list):
                    if param == 'model.expenseentryentity.expenseitem.id':
                        ids = [str(item.get('value', '')) for item in items]
                        return f"({resolver.get_expense_items_by_ids(ids)})"
                    elif param in ['model.org.id', 'model.company.id']:
                        ids = [str(item.get('value', '')) for item in items]
                        names = [resolver.get_org_name(id_) for id_ in ids]
                        return f"({'、'.join(names)})"
                    elif param == 'model.applier.id':
                        ids = [str(item.get('value', '')) for item in items]
                        names = [resolver.get_user_name(id_) for id_ in ids]
                        return f"({'、'.join(names)})"
            except json.JSONDecodeError:
                # 处理逗号分隔的ID字符串
                if param == 'model.expenseentryentity.expenseitem.id':
                    # 直接处理原始字符串中的ID列表
                    ids = [id_.strip() for id_ in value.strip('[]"\'').split(',')]
                    return f"({resolver.get_expense_items_by_ids(ids)})"
                elif param in ['model.org.id', 'model.company.id']:
                    ids = [id_.strip() for id_ in value.strip('[]"\'').split(',')]
                    names = [resolver.get_org_name(id_) for id_ in ids]
                    return f"({'、'.join(names)})"
                elif param == 'model.applier.id':
                    ids = [id_.strip() for id_ in value.strip('[]"\'').split(',')]
                    names = [resolver.get_user_name(id_) for id_ in ids]
                    return f"({'、'.join(names)})"
        
        # 处理单个值
        if param == 'model.expenseentryentity.expenseitem.id':
            return f"({resolver.get_expense_item(str(value))})"
        elif param in ['model.org.id', 'model.company.id']:
            return resolver.get_org_name(str(value))
        elif param == 'model.applier.id':
            return resolver.get_user_name(str(value))
        elif param == 'model.billno':
            return f"单据编号:{value}"
        elif param == 'model.loanamount':
            return f"金额:{value}"
    except Exception as e:
        print(f"解析条件值出错: {e}")
        return str(value)

def parse_participant(participant, resolver):
    if not participant:
        return []
    
    parsed = []
    for p in participant:
        if isinstance(p, dict):
            # Handle participant with role
            role_id = p.get('roleId', 'N/A')
            condition_exp = p.get('conditionExpression', '无条件')
            participant_value = p.get('value', 'N/A')
            
            # Parse participant value
            if participant_value.isdigit():  # Assuming it's a user ID
                participant_name = resolver.get_user_name(participant_value)
            else:
                participant_name = participant_value
            
            # Parse role info
            role_info = resolver.get_role_info(role_id) if role_id != 'N/A' else 'N/A'
            
            # Parse condition
            condition = parse_condition(condition_exp, resolver)
            
            parsed.append(f"{participant_name} (角色编号: {role_info}(条件: {condition})")
        else:
            # Simple participant (just user ID)
            parsed.append(resolver.get_user_name(p))
    
    return parsed

def parse_process_file(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # 解析流程基本信息
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
    
    # 解析资源数据
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

def build_dag(process_data, resolver):
    nodes = process_data.get("childShapes", [])
    graph = defaultdict(list)
    node_info = {}
    
    for node in nodes:
        try:
            node_id = node.get("resourceId", "N/A")
            properties = node.get("properties", {})
            
            node_info[node_id] = {
                "name": properties.get("name", "未命名"),
                "type": node["stencil"]["id"],
                "participant": parse_participant(properties.get("participant", {}).get("participant", []), resolver),
                "condition": parse_condition(properties.get("conditionalRule", "无条件"), resolver),
                "properties": {k: v for k, v in properties.items() if k not in ["participant", "conditionalRule"]}
            }
        except Exception as e:
            print(f"解析节点 {node.get('resourceId', '未知')} 出错: {e}")
    
    # 构建边
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
    resolver = DataResolver()
    
    try:
        workflow, process_data = parse_process_file(xml_file)
        graph, node_info = build_dag(process_data, resolver)
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
    finally:
        resolver.close()

if __name__ == "__main__":
    xml_file = input("请输入XML文件路径: ")
    main(xml_file)