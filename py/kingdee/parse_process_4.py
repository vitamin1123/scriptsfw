import json
from collections import defaultdict
import xml.etree.ElementTree as ET
import re
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
def get_ori_data():
    file_path = input("请输入XML文件路径：")
    tree = ET.parse(file_path)
    root = tree.getroot()

    # 找到Resources下的wf_resource元素
    resources = root.find('Resources')
    if resources is not None:
        wf_resource = resources.find('wf_resource')
        if wf_resource is not None:
            # 找到data元素
            data = wf_resource.find('data')
            if data is not None:
                # 获取data元素的文本内容
                data_content = data.text
                return data_content
            else:
                print("未找到data元素。")
        else:
            print("未找到wf_resource元素。")
    else:
        print("未找到Resources元素。")

def extract_properties(data):
    properties = data.get('properties', {})
    print(f"业务ID: {properties.get('businessId', 'N/A')}")
    print(f"单据名称: {properties.get('entraBillName', 'N/A')}")
    
    # 提取并显示启动条件
    startup_cond = properties.get('startupcondrule', {})
    condition_rule = startup_cond.get('conditionRule', 'N/A')
    entry_entities = startup_cond.get('entryentity', [])
    
    # 拼接entryentity表达式
    if entry_entities:
        sorted_entries = sorted(entry_entities, key=lambda x: x.get('seq', 0))
        expr_parts = []
        for entry in sorted_entries:
            # 处理括号
            if 'leftbracket' in entry:
                expr_parts.append(entry['leftbracket'])
            
            # 添加子表达式
            expr_parts.append(f"{entry.get('paramnumber', '')} {entry.get('operation', '')} {entry.get('value', '')}")
            
            # 处理右括号
            if 'rightbracket' in entry:
                expr_parts.append(entry['rightbracket'])
            
            # 添加逻辑运算符(第一个元素不需要)
            if expr_parts and 'logic' in entry:
                expr_parts.append(f" {entry['logic']} ")
        
        built_expr = ''.join(expr_parts)
        print(f"原始conditionRule: \n {condition_rule}")
        print(f"拼接后的表达式: \n {built_expr}")
    
    if condition_rule != 'N/A':
        # 调用parse_condition_expression处理条件表达式
        bill_type = properties.get('entraBill', '').replace('er_', '')
        condition_rule = parse_condition_expression(condition_rule, bill_type)
        print(f"解析后的启动条件: \n {condition_rule}")

def build_dag(data):
    nodes = data.get('childShapes', [])
    graph = defaultdict(list)
    node_info = {}
    
    for node in nodes:
        node_id = node.get('resourceId')
        node_info[node_id] = node
        
    for node in nodes:
        node_id = node.get('resourceId')
        for outgoing in node.get('outgoing', []):
            target = outgoing.get('resourceId')
            if target in node_info:
                graph[node_id].append(target)
    
    return graph, node_info

def find_all_paths(graph, node_info, path, current_node, all_paths):
    path.append(current_node)
    
    if not graph[current_node]:
        all_paths.append(list(path))
    else:
        for neighbor in graph[current_node]:
            find_all_paths(graph, node_info, path, neighbor, all_paths)
    
    path.pop()

def parse_condition_expression(expr, bill_type):
    """处理条件表达式，转换为中文描述
    Args:
        expr: 原始表达式字符串，如${model.detailtype != "biztype_contract" && ...}
        bill_type: 单据类型，从properties-entraBill获取
    Returns:
        转换后的中文表达式
    """
    original_expr = expr  # 保存原始表达式
    
    # 1. 去除${}包装
    expr = expr.strip().strip('${}').strip()
    
    # 初始化DataResolver
    resolver = DataResolver()
    
    # 2. 转换运算符
    op_map = {
        '!=': '不等于',
        '==': '等于',
        '&&': '且',
        '||': '或',
        'IN': '在',
        'NI': '不在'
    }
    for op, name in op_map.items():
        expr = expr.replace(op, name)
    
    # 3. 处理model.前缀和.id/.name后缀
    def replace_field(match):
        field = match.group(1)
        # 去掉model.前缀
        field = field.replace('model.', '')
        # 去掉.id或.name后缀
        if field.endswith('.id') or field.endswith('.name'):
            field = field[:-3]
        # print('bill_type: ',bill_type)
        # 根据单据类型加载对应的json文件
        try:
            with open(f"{bill_type}.txt", 'r', encoding='utf-8') as f:
                # print('找到文件了')
                field_data = json.load(f)
                # 获取p数组的第二个元素下的st数组
                if len(field_data) > 1 and 'p' in field_data[1]:
                    p_array = field_data[1]['p']
                    if len(p_array) > 1 and 'st' in p_array[1]:
                        st_array = p_array[1]['st']
                        # 遍历st数组查找匹配字段
                        for item in st_array:
                            if isinstance(item, list) and len(item) > 0 and item[0] == field:
                                if len(item) > 1 and isinstance(item[1], dict) and 'zh_CN' in item[1]:
                                    # print('fuck: ',item)
                                    return item[1]['zh_CN']
                return field
        except:
            return field
    
    # 匹配所有model.开头的字段引用
    expr = re.sub(r'(model\.[\w\.]+)(?:\.id|\.name)?', replace_field, expr)
    
        # 处理组织ID替换
    org_keywords = ['公司', '组织', '部门']
    for keyword in org_keywords:
        pattern = re.compile(fr'({keyword}s*==s*)("[\d,]+"|\d+)')
        
        def replace_org_ids(match):
            prefix = match.group(1)
            id_str = match.group(2).strip('"')
            
            # 处理JSON数组格式的value
            if id_str.startswith('[') and id_str.endswith(']'):
                try:
                    items = json.loads(id_str)
                    if isinstance(items, list):
                        resolved_items = []
                        for item in items:
                            if isinstance(item, dict):
                                number = item.get('number', '')
                                alias = item.get('alias', '')
                                resolved_items.append(f"{number}{alias}")
                        return f"{prefix}" + '"' + '、'.join(resolved_items) + '"'
                except json.JSONDecodeError:
                    pass
            
            # 处理逗号分隔的ID列表
            if ',' in id_str:
                ids = [id_.strip() for id_ in id_str.split(',')]
                names = [resolver.get_org_name(id_) for id_ in ids]
                print('names: ',names)
                return f"{prefix}" + '"' + '、'.join(names) + '"'
            else:  # 处理单个ID
                return f"{prefix}" + '"' + resolver.get_org_name(id_str) + '"'
        
        expr = pattern.sub(replace_org_ids, expr)
    
    # 返回原始表达式和转换后的表达式，换行显示
    return f"原始表达式: {original_expr}\n转换后表达式: {expr}"

def print_paths(graph, node_info):
    start_nodes = [node for node in node_info if all(node not in targets for targets in graph.values())]
    all_paths = []
    
    for start in start_nodes:
        find_all_paths(graph, node_info, [], start, all_paths)
    
    print("\n所有可能的路径:")
    for idx, path in enumerate(all_paths, 1):
        print(f"路径 {idx}:")
        for node in path:
            node_data = node_info[node]
            name = node_data.get('properties', {}).get('name', '未命名')
            number = node_data.get('properties', {}).get('number', 'N/A')
            stencil_id = node_data.get('stencil', {}).get('id', 'N/A')
            print(f"  - {name} ({stencil_id}) ")
            # print(f"  - {name} (编号: {number}, 节点类型: {stencil_id})")
        print()

if __name__ == '__main__':
    resolver = DataResolver()
    try:
        ori_data = get_ori_data()
        if ori_data:
            data = json.loads(ori_data)
            extract_properties(data)
            graph, node_info = build_dag(data)
            print_paths(graph, node_info)
    finally:
        resolver.close()

        